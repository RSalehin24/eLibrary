//! Sign-in with email and password. Every failure is the same `Rejected` (INV-IDN-008): an
//! unknown account, a wrong password and an inactive account cannot be told apart, and the
//! password hash is checked on every path so the timing is alike.

use contracts_ids::UserId;
use domain_credentials::PasswordHash;
use platform_random::{RandomError, RandomSource, to_hex, uuid_v7};
use platform_time::{Clock, Instant};
use sha2::{Digest, Sha256};
use sqlx::PgPool;
use thiserror::Error;

use crate::audit::{self, AuditEntry};
use crate::session::{self, IssuedSession, NewSession, SessionError, SessionState};
use crate::throttle::{MAX_ATTEMPTS, record_attempt};
use crate::users::{self, SignInRecord};

#[derive(Debug, Error)]
pub enum SignInError {
    #[error("database: {0}")]
    Database(#[from] sqlx::Error),
    #[error("session: {0}")]
    Session(#[from] SessionError),
    #[error("randomness: {0}")]
    Random(#[from] RandomError),
    #[error("password check did not finish")]
    HashTask,
}

/// What was typed.
#[derive(Debug, Clone, Copy)]
pub struct Credentials<'a> {
    pub email: &'a str,
    pub password: &'a str,
}

/// Where it came from, for throttling and the audit log (an address prefix, never a full address).
#[derive(Debug, Clone, Copy, Default)]
pub struct Client<'a> {
    pub address: Option<&'a str>,
}

/// When and from where; bundled so the helpers stay within three parameters.
#[derive(Debug, Clone, Copy)]
struct Context<'a> {
    now: Instant,
    client: Client<'a>,
}

/// The service's collaborators, injected so tests control time and randomness.
pub struct Services<'a, C: Clock, R: RandomSource> {
    pub pool: &'a PgPool,
    pub clock: &'a C,
    pub random: &'a R,
    /// Checked when the account does not exist, so unknown and known accounts cost the same.
    pub dummy_hash: &'a PasswordHash,
}

#[derive(Debug, PartialEq, Eq)]
pub enum SignInOutcome {
    SignedIn(IssuedSession),
    /// The password was right but the account requires TOTP: the session is `pending_totp`.
    SecondFactorRequired(IssuedSession),
    Rejected,
    Throttled,
}

/// # Errors
/// Infrastructure failures only; wrong credentials are an `Ok(Rejected)`.
pub async fn sign_in<C: Clock, R: RandomSource>(
    services: &Services<'_, C, R>,
    credentials: Credentials<'_>,
    client: Client<'_>,
) -> Result<SignInOutcome, SignInError> {
    let now = services.clock.now();
    let context = Context { now, client };
    let key = attempt_key(credentials.email);
    if record_attempt(services.pool, &key, now).await? > MAX_ATTEMPTS {
        return Ok(SignInOutcome::Throttled);
    }
    let record = users::find_for_sign_in(services.pool, credentials.email).await?;
    let password_ok =
        check_password(services.dummy_hash, record.as_ref(), credentials.password).await?;
    match record {
        Some(record) if password_ok && record.status == "active" => {
            start_session(services, &record, context).await
        }
        _ => reject(services, &key, context).await,
    }
}

// why: the key is a hash, so emails are not stored in the throttle table.
fn attempt_key(email: &str) -> String {
    let digest = Sha256::digest(email.to_lowercase().as_bytes());
    to_hex(&digest)
}

async fn check_password(
    dummy: &PasswordHash,
    record: Option<&SignInRecord>,
    password: &str,
) -> Result<bool, SignInError> {
    let stored = record
        .and_then(|record| record.password_hash.as_deref())
        .and_then(PasswordHash::from_stored);
    let known = stored.is_some();
    let hash = stored.unwrap_or_else(|| dummy.clone());
    let attempt = password.to_owned();
    // why: Argon2 is CPU-bound; keep it off the async worker threads.
    let verified = tokio::task::spawn_blocking(move || hash.verify(&attempt))
        .await
        .map_err(|_| SignInError::HashTask)?;
    Ok(verified && known)
}

async fn start_session<C: Clock, R: RandomSource>(
    services: &Services<'_, C, R>,
    record: &SignInRecord,
    context: Context<'_>,
) -> Result<SignInOutcome, SignInError> {
    let issued = persist_session(services, record, context).await?;
    Ok(match issued.state {
        SessionState::Authenticated => SignInOutcome::SignedIn(issued),
        SessionState::PendingTotp => SignInOutcome::SecondFactorRequired(issued),
    })
}

/// The session row and its audit row commit together or not at all.
async fn persist_session<C: Clock, R: RandomSource>(
    services: &Services<'_, C, R>,
    record: &SignInRecord,
    context: Context<'_>,
) -> Result<IssuedSession, SignInError> {
    let Context { now, client } = context;
    let state = if record.totp_required {
        SessionState::PendingTotp
    } else {
        SessionState::Authenticated
    };
    let id = uuid_v7(now.unix_millis(), services.random)?;
    let new = NewSession {
        id,
        user_id: record.id,
        state,
        now,
        random: services.random,
    };
    let mut transaction = services.pool.begin().await?;
    let issued = session::create(&mut transaction, new).await?;
    let subject = UserId::from_uuid(record.id).to_string();
    let entry = AuditEntry {
        at: now,
        actor: &subject,
        subject: Some(&subject),
        action: "sign_in",
        address: client.address,
    };
    audit::record(&mut transaction, entry).await?;
    transaction.commit().await?;
    Ok(issued)
}

async fn reject<C: Clock, R: RandomSource>(
    services: &Services<'_, C, R>,
    key: &str,
    context: Context<'_>,
) -> Result<SignInOutcome, SignInError> {
    let Context { now, client } = context;
    let mut connection = services.pool.acquire().await?;
    let entry = AuditEntry {
        at: now,
        actor: "anonymous",
        subject: Some(key),
        action: "sign_in_failed",
        address: client.address,
    };
    audit::record(&mut connection, entry).await?;
    Ok(SignInOutcome::Rejected)
}
