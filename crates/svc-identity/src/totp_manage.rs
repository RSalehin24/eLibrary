//! Own-account TOTP: enrolment (setup, confirm), disable and reveal. A `pending` secret never
//! counts as a second factor; disable and reveal re-authenticate with password and code.

use contracts_http::CommonErrorCode;
use contracts_ids::UserId;
use domain_credentials::{Attempt, PasswordHash, TotpError, TotpSecret, TotpStep, verify_code};
use platform_random::{OsRandom, RandomError, RandomSource};
use platform_time::Instant;
use serde::Serialize;
use sqlx::{PgConnection, PgPool, Row};
use thiserror::Error;
use uuid::Uuid;

use crate::audit::{self, AuditEntry};
use crate::capabilities::totp_state;
use crate::throttle::{MAX_ATTEMPTS, record_attempt};
use crate::totp_verify::throttle_key;
use crate::vault::{self, Plain, VaultError, VaultKey, seal};

const SECRET_BYTES: usize = 20;
const ISSUER: &str = "eLibrary";

#[derive(Debug, Error)]
pub(crate) enum ManageError {
    #[error("database: {0}")]
    Database(#[from] sqlx::Error),
    #[error("vault: {0}")]
    Vault(#[from] VaultError),
    #[error("secret: {0}")]
    Secret(#[from] TotpError),
    #[error("randomness: {0}")]
    Random(#[from] RandomError),
    #[error("password check did not finish")]
    HashTask,
}

/// What a request needs: the pool, the vault key and the clock reading.
#[derive(Clone, Copy)]
pub(crate) struct Manage<'a> {
    pub pool: &'a PgPool,
    pub key: &'a VaultKey,
    pub now: Instant,
}

/// How a request ended, apart from infrastructure failures.
pub(crate) enum Outcome<T> {
    Done(T),
    BadPassword,
    BadCode,
    Throttled,
    /// The new password breaks the policy.
    Weak,
    Refused(CommonErrorCode),
}

#[derive(Serialize)]
pub(crate) struct Enrolment {
    secret: String,
    provisioning_uri: String,
}

#[derive(Serialize)]
pub(crate) struct Revealed {
    secret: String,
}

/// The password and code typed to re-authenticate.
#[derive(Clone, Copy)]
pub(crate) struct Reauth<'a> {
    pub user: Uuid,
    pub password: &'a str,
    pub code: &'a str,
}

pub(crate) async fn status(pool: &PgPool, user: Uuid) -> Result<&'static str, sqlx::Error> {
    let row = sqlx::query(
        "select u.totp_required, coalesce(t.state, 'none') as state
         from users u left join totp t on t.user_id = u.id where u.id = $1",
    )
    .bind(user)
    .fetch_one(pool)
    .await?;
    let state: String = row.try_get("state")?;
    Ok(totp_state(&state, row.try_get("totp_required")?))
}

fn encode(text: &str) -> String {
    text.bytes()
        .map(|byte| match byte {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'.' | b'_' | b'~' => {
                char::from(byte).to_string()
            }
            other => format!("%{other:02X}"),
        })
        .collect()
}

fn provisioning_uri(email: &str, secret: &TotpSecret) -> String {
    let label = encode(&format!("{ISSUER}:{email}"));
    let secret = secret.to_base32();
    format!("otpauth://totp/{label}?secret={secret}&issuer={ISSUER}&digits=6&period=30")
}

/// Starts (or restarts) enrolment: stores a new pending secret and shows it this once.
pub(crate) async fn setup(m: Manage<'_>, user: Uuid) -> Result<Outcome<Enrolment>, ManageError> {
    let mut transaction = m.pool.begin().await?;
    let state: Option<String> =
        sqlx::query_scalar("select state from totp where user_id = $1 for update")
            .bind(user)
            .fetch_optional(&mut *transaction)
            .await?;
    if state.as_deref() == Some("enabled") {
        return Ok(Outcome::Refused(CommonErrorCode::InvalidTransition));
    }
    let bytes = store_pending(&mut transaction, m.key, user).await?;
    let email = email_of(&mut transaction, user).await?;
    audit_event(
        &mut transaction,
        Event {
            at: m.now,
            user,
            action: "totp_setup",
        },
    )
    .await?;
    transaction.commit().await?;
    let secret = TotpSecret::from_bytes(bytes)?;
    Ok(Outcome::Done(Enrolment {
        provisioning_uri: provisioning_uri(&email, &secret),
        secret: secret.to_base32(),
    }))
}

async fn email_of(connection: &mut PgConnection, user: Uuid) -> Result<String, sqlx::Error> {
    sqlx::query_scalar("select email from users where id = $1")
        .bind(user)
        .fetch_one(connection)
        .await
}

/// Replaces the pending secret with a fresh one and returns its bytes.
async fn store_pending(
    connection: &mut PgConnection,
    key: &VaultKey,
    user: Uuid,
) -> Result<Vec<u8>, ManageError> {
    let mut bytes = vec![0_u8; SECRET_BYTES];
    OsRandom.fill(&mut bytes)?;
    let sealed = seal(
        key,
        Plain {
            owner: user,
            bytes: &bytes,
        },
        &OsRandom,
    )?;
    sqlx::query(
        "insert into totp (user_id, secret_enc, state) values ($1, $2, 'pending')
         on conflict (user_id) do update set secret_enc = $2, state = 'pending',
             confirmed_at = null, last_accepted_step = null, failed_count = 0",
    )
    .bind(user)
    .bind(sealed)
    .execute(connection)
    .await?;
    Ok(bytes)
}

/// The account, the step of the code that proved the secret, and when.
#[derive(Clone, Copy)]
struct Enable {
    at: Instant,
    user: Uuid,
    step: i64,
}

async fn enable(connection: &mut PgConnection, change: Enable) -> Result<(), sqlx::Error> {
    sqlx::query(
        "update totp set state = 'enabled', confirmed_at = $2, last_accepted_step = $3
         where user_id = $1",
    )
    .bind(change.user)
    .bind(change.at.to_offset_date_time())
    .bind(change.step)
    .execute(connection)
    .await
    .map(|_| ())
}

/// Why a confirm failed: a wrong code, or no enrolment to confirm.
async fn rejection(connection: &mut PgConnection, user: Uuid) -> Result<Outcome<()>, ManageError> {
    let pending = has_state(connection, user, "pending").await?;
    Ok(if pending {
        Outcome::BadCode
    } else {
        Outcome::Refused(CommonErrorCode::InvalidTransition)
    })
}

/// Enables TOTP when the code matches the pending secret.
pub(crate) async fn confirm(
    m: Manage<'_>,
    user: Uuid,
    code: &str,
) -> Result<Outcome<()>, ManageError> {
    if throttled(&m, user).await? {
        return Ok(Outcome::Throttled);
    }
    let mut transaction = m.pool.begin().await?;
    let Some(step) = check(&mut transaction, &m, Probe::pending(user, code)).await? else {
        return rejection(&mut transaction, user).await;
    };
    enable(
        &mut transaction,
        Enable {
            at: m.now,
            user,
            step,
        },
    )
    .await?;
    audit_event(
        &mut transaction,
        Event {
            at: m.now,
            user,
            action: "totp_enabled",
        },
    )
    .await?;
    transaction.commit().await?;
    Ok(Outcome::Done(()))
}

/// Turns TOTP off for an account that does not require it.
pub(crate) async fn disable(m: Manage<'_>, auth: Reauth<'_>) -> Result<Outcome<()>, ManageError> {
    let mut transaction = m.pool.begin().await?;
    if let Some(stop) = reauthenticate(&mut transaction, &m, auth).await? {
        return Ok(stop);
    }
    let required: bool = sqlx::query_scalar("select totp_required from users where id = $1")
        .bind(auth.user)
        .fetch_one(&mut *transaction)
        .await?;
    if required {
        return Ok(Outcome::Refused(CommonErrorCode::Forbidden));
    }
    sqlx::query("delete from totp where user_id = $1")
        .bind(auth.user)
        .execute(&mut *transaction)
        .await?;
    audit_event(&mut transaction, m.event(auth.user, "totp_disabled")).await?;
    transaction.commit().await?;
    Ok(Outcome::Done(()))
}

/// Shows the enabled secret again after re-authentication.
pub(crate) async fn reveal(
    m: Manage<'_>,
    auth: Reauth<'_>,
) -> Result<Outcome<Revealed>, ManageError> {
    let mut transaction = m.pool.begin().await?;
    if let Some(stop) = reauthenticate(&mut transaction, &m, auth).await? {
        return Ok(stop);
    }
    let stored: Vec<u8> = sqlx::query_scalar("select secret_enc from totp where user_id = $1")
        .bind(auth.user)
        .fetch_one(&mut *transaction)
        .await?;
    let secret = TotpSecret::from_bytes(vault::open(m.key, auth.user, &stored)?)?;
    audit_event(&mut transaction, m.event(auth.user, "totp_revealed")).await?;
    transaction.commit().await?;
    Ok(Outcome::Done(Revealed {
        secret: secret.to_base32(),
    }))
}

/// Checks password then code (the step is recorded); `Some` is the outcome that stops the request.
async fn reauthenticate<T>(
    connection: &mut PgConnection,
    m: &Manage<'_>,
    auth: Reauth<'_>,
) -> Result<Option<Outcome<T>>, ManageError> {
    if throttled(m, auth.user).await? {
        return Ok(Some(Outcome::Throttled));
    }
    if !password_ok(m.pool, auth.user, auth.password).await? {
        return Ok(Some(Outcome::BadPassword));
    }
    let step = check(
        connection,
        m,
        Probe {
            user: auth.user,
            state: "enabled",
            code: auth.code,
        },
    )
    .await?;
    Ok(step.is_none().then_some(Outcome::BadCode))
}

pub(crate) async fn throttled(m: &Manage<'_>, user: Uuid) -> Result<bool, sqlx::Error> {
    Ok(record_attempt(m.pool, &throttle_key(user), m.now).await? > MAX_ATTEMPTS)
}

pub(crate) async fn password_ok(
    pool: &PgPool,
    user: Uuid,
    attempt: &str,
) -> Result<bool, ManageError> {
    let stored: Option<String> =
        sqlx::query_scalar("select password_hash from credentials where user_id = $1")
            .bind(user)
            .fetch_optional(pool)
            .await?;
    let Some(hash) = stored.as_deref().and_then(PasswordHash::from_stored) else {
        return Ok(false);
    };
    let attempt = attempt.to_owned();
    // why: Argon2 is CPU-bound; keep it off the async worker threads.
    tokio::task::spawn_blocking(move || hash.verify(&attempt))
        .await
        .map_err(|_| ManageError::HashTask)
}

async fn has_state(
    connection: &mut PgConnection,
    user: Uuid,
    state: &str,
) -> Result<bool, sqlx::Error> {
    sqlx::query_scalar("select exists (select 1 from totp where user_id = $1 and state = $2)")
        .bind(user)
        .bind(state)
        .fetch_one(connection)
        .await
}

/// Whose secret, in which state, and the code typed for it.
#[derive(Clone, Copy)]
pub(crate) struct Probe<'a> {
    pub user: Uuid,
    pub state: &'a str,
    pub code: &'a str,
}

impl<'a> Probe<'a> {
    fn pending(user: Uuid, code: &'a str) -> Self {
        Self {
            user,
            state: "pending",
            code,
        }
    }
}

/// Locks the TOTP row in `state` and checks the code; the accepted step, if any (not yet stored).
pub(crate) async fn check(
    connection: &mut PgConnection,
    m: &Manage<'_>,
    probe: Probe<'_>,
) -> Result<Option<i64>, ManageError> {
    let Probe { user, state, code } = probe;
    let row = sqlx::query(
        "select secret_enc, last_accepted_step from totp where user_id = $1 and state = $2 for update",
    )
    .bind(user)
    .bind(state)
    .fetch_optional(&mut *connection)
    .await?;
    let Some(row) = row else { return Ok(None) };
    let stored: Vec<u8> = row.try_get("secret_enc")?;
    let last: Option<i64> = row.try_get("last_accepted_step")?;
    let secret = TotpSecret::from_bytes(vault::open(m.key, user, &stored)?)?;
    let attempt = Attempt {
        code,
        now: m.now,
        last_accepted: last.and_then(|step| u64::try_from(step).ok()).map(TotpStep),
    };
    let Ok(step) = verify_code(&secret, attempt) else {
        return Ok(None);
    };
    let step = i64::try_from(step.0).unwrap_or(i64::MAX);
    sqlx::query("update totp set last_accepted_step = $2 where user_id = $1")
        .bind(user)
        .bind(step)
        .execute(connection)
        .await?;
    Ok(Some(step))
}

impl<'a> Manage<'a> {
    pub(crate) fn event(&self, user: Uuid, action: &'a str) -> Event<'a> {
        Event {
            at: self.now,
            user,
            action,
        }
    }
}

/// One audited action of a user on their own account.
#[derive(Clone, Copy)]
pub(crate) struct Event<'a> {
    at: Instant,
    user: Uuid,
    action: &'a str,
}

pub(crate) async fn audit_event(
    connection: &mut PgConnection,
    event: Event<'_>,
) -> Result<(), sqlx::Error> {
    let Event { at, user, action } = event;
    let subject = UserId::from_uuid(user).to_string();
    let entry = AuditEntry {
        at,
        actor: &subject,
        subject: Some(&subject),
        action,
        address: None,
    };
    audit::record(connection, entry).await
}
