//! Setting a password through an emailed link: accepting an invitation and the two steps of a
//! password reset (REQ-IDN-001, 002, 008). Unknown, used, expired and superseded links all look
//! the same to the caller (`link_invalid`).

use domain_credentials::{Password, PasswordHash, SALT_BYTES};
use platform_random::{OsRandom, RandomSource, to_hex};
use platform_time::Instant;
use sha2::{Digest, Sha256};
use sqlx::{PgConnection, PgPool, Row};
use uuid::Uuid;

use crate::admin_change::{Request, audit_change};
use crate::links::{Issue, LinkError, Purpose, issue, nonce_matches, token_hash};
use crate::throttle::{MAX_ATTEMPTS, record_attempt};
use crate::vault::VaultKey;

/// The pool, vault key and clock reading.
#[derive(Clone, Copy)]
pub(crate) struct Context<'a> {
    pub pool: &'a PgPool,
    pub key: &'a VaultKey,
    pub now: Instant,
}

/// How a link redemption ended, apart from infrastructure failures.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Redeemed {
    /// The password was set; `totp_required` tells the client whether to continue with setup.
    Done {
        totp_required: bool,
    },
    LinkInvalid,
    WeakPassword,
}

async fn hashed(password: Password) -> Result<PasswordHash, LinkError> {
    let mut salt = [0_u8; SALT_BYTES];
    OsRandom.fill(&mut salt)?;
    // why: Argon2 is CPU-bound; keep it off the async worker threads.
    tokio::task::spawn_blocking(move || PasswordHash::create(&password, &salt))
        .await
        .map_err(|_| LinkError::HashTask)?
        .map_err(|_| LinkError::HashTask)
}

/// The locked link row a token names, if it can still be redeemed for `purpose`.
struct Open {
    link: Uuid,
    user: Uuid,
    status: String,
    totp_required: bool,
}

async fn open_link(
    connection: &mut PgConnection,
    now: Instant,
    redemption: (&str, Purpose),
) -> Result<Option<Open>, sqlx::Error> {
    let (token, purpose) = redemption;
    let row = sqlx::query(
        "select l.id, l.user_id, l.nonce, u.status, u.totp_required
         from links l join users u on u.id = l.user_id
         where l.token_hash = $1 and l.purpose = $2 and l.state = 'issued' and l.expires_at > $3
         for update of l",
    )
    .bind(token_hash(token))
    .bind(purpose.as_str())
    .bind(now.to_offset_date_time())
    .fetch_optional(connection)
    .await?;
    let Some(row) = row else { return Ok(None) };
    let nonce: Vec<u8> = row.try_get("nonce")?;
    if !nonce_matches(token, &nonce) {
        return Ok(None);
    }
    Ok(Some(Open {
        link: row.try_get("id")?,
        user: row.try_get("user_id")?,
        status: row.try_get("status")?,
        totp_required: row.try_get("totp_required")?,
    }))
}

async fn consume(connection: &mut PgConnection, link: Uuid) -> Result<(), sqlx::Error> {
    sqlx::query("update links set state = 'consumed' where id = $1")
        .bind(link)
        .execute(connection)
        .await
        .map(|_| ())
}

fn system_request<'a>(context: &Context<'a>, user: Uuid) -> Request<'a> {
    Request {
        pool: context.pool,
        now: context.now,
        actor: user,
        target: user,
    }
}

/// Stores the first password, activates the account and uses up the link.
async fn activate(
    connection: &mut PgConnection,
    context: &Context<'_>,
    setup: (&Open, &PasswordHash),
) -> Result<(), LinkError> {
    let (open, hash) = setup;
    let at = context.now.to_offset_date_time();
    sqlx::query("insert into credentials (user_id, password_hash, changed_at) values ($1, $2, $3)")
        .bind(open.user)
        .bind(hash.as_str())
        .bind(at)
        .execute(&mut *connection)
        .await?;
    sqlx::query(
        "update users set status = 'active', revision = revision + 1, updated_at = $2 where id = $1",
    )
    .bind(open.user)
    .bind(at)
    .execute(&mut *connection)
    .await?;
    consume(connection, open.link).await?;
    audit_change(
        connection,
        system_request(context, open.user),
        "invite_accepted",
    )
    .await?;
    Ok(())
}

/// Activates an invited account with the chosen password.
pub(crate) async fn accept_invite(
    context: Context<'_>,
    token: &str,
    password: &str,
) -> Result<Redeemed, LinkError> {
    let Ok(password) = Password::parse(password) else {
        return Ok(Redeemed::WeakPassword);
    };
    let hash = hashed(password).await?;
    let mut transaction = context.pool.begin().await?;
    let found = open_link(&mut transaction, context.now, (token, Purpose::Invite)).await?;
    let Some(open) = found.filter(|open| open.status == "invited") else {
        return Ok(Redeemed::LinkInvalid);
    };
    activate(&mut transaction, &context, (&open, &hash)).await?;
    transaction.commit().await?;
    Ok(Redeemed::Done {
        totp_required: open.totp_required,
    })
}

/// Stores the new password, ends the account's sessions and uses up the link.
async fn apply_reset(
    connection: &mut PgConnection,
    context: &Context<'_>,
    reset: (&Open, &PasswordHash),
) -> Result<(), LinkError> {
    let (open, hash) = reset;
    let at = context.now.to_offset_date_time();
    sqlx::query("update credentials set password_hash = $2, changed_at = $3 where user_id = $1")
        .bind(open.user)
        .bind(hash.as_str())
        .bind(at)
        .execute(&mut *connection)
        .await?;
    sqlx::query("update sessions set revoked_at = $2 where user_id = $1 and revoked_at is null")
        .bind(open.user)
        .bind(at)
        .execute(&mut *connection)
        .await?;
    consume(connection, open.link).await?;
    audit_change(
        connection,
        system_request(context, open.user),
        "password_reset",
    )
    .await?;
    Ok(())
}

/// Sets a new password from a reset link and ends every session of the account.
pub(crate) async fn confirm_reset(
    context: Context<'_>,
    token: &str,
    password: &str,
) -> Result<Redeemed, LinkError> {
    let Ok(password) = Password::parse(password) else {
        return Ok(Redeemed::WeakPassword);
    };
    let hash = hashed(password).await?;
    let mut transaction = context.pool.begin().await?;
    let found = open_link(&mut transaction, context.now, (token, Purpose::Reset)).await?;
    let Some(open) = found.filter(|open| open.status == "active") else {
        return Ok(Redeemed::LinkInvalid);
    };
    apply_reset(&mut transaction, &context, (&open, &hash)).await?;
    transaction.commit().await?;
    Ok(Redeemed::Done {
        totp_required: open.totp_required,
    })
}

// why: a hash key keeps addresses out of the throttle table's readable keys, like sign-in does.
fn reset_key(email: &str) -> String {
    to_hex(&Sha256::digest(
        format!("reset:{}", email.to_lowercase()).as_bytes(),
    ))
}

/// Starts a reset for a known, active account. The caller answers 202 either way; `false`
/// means the per-address limit was reached (the caller answers `rate_limited`).
pub(crate) async fn request_reset(context: Context<'_>, email: &str) -> Result<bool, LinkError> {
    let attempts = record_attempt(context.pool, &reset_key(email), context.now).await?;
    if attempts > MAX_ATTEMPTS {
        return Ok(false);
    }
    let mut transaction = context.pool.begin().await?;
    let found: Option<(Uuid, String)> = sqlx::query_as(
        "select u.id, u.language from users u join credentials c on c.user_id = u.id
         where lower(u.email) = lower($1) and u.status = 'active' for update of u",
    )
    .bind(email)
    .fetch_optional(&mut *transaction)
    .await?;
    if let Some((user, language)) = found {
        let link = Issue {
            request: system_request(&context, user),
            purpose: Purpose::Reset,
            language: &language,
        };
        issue(&mut transaction, context.key, link).await?;
        audit_change(&mut transaction, link.request, "password_reset_requested").await?;
    }
    transaction.commit().await?;
    Ok(true)
}
