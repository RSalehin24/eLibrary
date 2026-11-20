//! Changing the own password: re-authenticates with the current password (and a TOTP code when
//! TOTP is on), keeps the calling session and revokes every other one.

use domain_credentials::{Password, PasswordHash, SALT_BYTES};
use platform_random::{OsRandom, RandomSource};
use platform_time::Instant;
use sqlx::PgConnection;

use crate::session::LiveSession;
use crate::totp_manage::{
    Manage, ManageError, Outcome, Probe, audit_event, check, password_ok, throttled,
};

/// What was typed, and the session it was typed in.
#[derive(Clone, Copy)]
pub(crate) struct Change<'a> {
    pub session: &'a LiveSession,
    pub current: &'a str,
    pub new: &'a str,
    pub code: Option<&'a str>,
}

pub(crate) async fn change_password(
    m: Manage<'_>,
    change: Change<'_>,
) -> Result<Outcome<()>, ManageError> {
    let user = change.session.user_id;
    if throttled(&m, user).await? {
        return Ok(Outcome::Throttled);
    }
    if !password_ok(m.pool, user, change.current).await? {
        return Ok(Outcome::BadPassword);
    }
    let mut transaction = m.pool.begin().await?;
    if !second_factor_ok(&mut transaction, &m, change).await? {
        return Ok(Outcome::BadCode);
    }
    let Ok(password) = Password::parse(change.new) else {
        return Ok(Outcome::Weak);
    };
    let hash = hashed(password).await?;
    store(
        &mut transaction,
        &m,
        Stored {
            session: change.session,
            hash: &hash,
        },
    )
    .await?;
    transaction.commit().await?;
    Ok(Outcome::Done(()))
}

/// True when TOTP is off, or the typed code is valid (its step is recorded).
async fn second_factor_ok(
    connection: &mut PgConnection,
    m: &Manage<'_>,
    change: Change<'_>,
) -> Result<bool, ManageError> {
    let user = change.session.user_id;
    let enabled: bool = sqlx::query_scalar(
        "select exists (select 1 from totp where user_id = $1 and state = 'enabled')",
    )
    .bind(user)
    .fetch_one(&mut *connection)
    .await?;
    if !enabled {
        return Ok(true);
    }
    let Some(code) = change.code else {
        return Ok(false);
    };
    let probe = Probe {
        user,
        state: "enabled",
        code,
    };
    Ok(check(connection, m, probe).await?.is_some())
}

async fn hashed(password: Password) -> Result<PasswordHash, ManageError> {
    let mut salt = [0_u8; SALT_BYTES];
    OsRandom.fill(&mut salt)?;
    // why: Argon2 is CPU-bound; keep it off the async worker threads.
    tokio::task::spawn_blocking(move || PasswordHash::create(&password, &salt))
        .await
        .map_err(|_| ManageError::HashTask)?
        .map_err(|_| ManageError::HashTask)
}

/// Writes the new hash, revokes the user's other sessions and audits, in the caller's transaction.
async fn store(
    connection: &mut PgConnection,
    m: &Manage<'_>,
    stored: Stored<'_>,
) -> Result<(), ManageError> {
    let Stored { session, hash } = stored;
    sqlx::query("update credentials set password_hash = $2, changed_at = $3 where user_id = $1")
        .bind(session.user_id)
        .bind(hash.as_str())
        .bind(m.now.to_offset_date_time())
        .execute(&mut *connection)
        .await?;
    revoke_others(connection, session, m.now).await?;
    audit_event(connection, m.event(session.user_id, "password_changed")).await?;
    Ok(())
}

/// The session that changed the password and the hash to keep.
#[derive(Clone, Copy)]
struct Stored<'a> {
    session: &'a LiveSession,
    hash: &'a PasswordHash,
}

async fn revoke_others(
    connection: &mut PgConnection,
    session: &LiveSession,
    at: Instant,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "update sessions set revoked_at = $3 where user_id = $1 and id <> $2 and revoked_at is null",
    )
    .bind(session.user_id)
    .bind(session.id)
    .bind(at.to_offset_date_time())
    .execute(connection)
    .await
    .map(|_| ())
}
