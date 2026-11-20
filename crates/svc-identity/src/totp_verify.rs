//! Completing sign-in with a TOTP code (REQ-IDN-004, INV-IDN-005): the pending session becomes
//! authenticated only when the code is valid and its step is newer than the last accepted one.

use contracts_ids::UserId;
use domain_credentials::{Attempt, TotpError, TotpSecret, TotpStep, verify_code};
use platform_random::to_hex;
use platform_time::Instant;
use sha2::{Digest, Sha256};
use sqlx::{PgConnection, PgPool, Row};
use thiserror::Error;
use uuid::Uuid;

use crate::audit::{self, AuditEntry};
use crate::session::{self, LiveSession, PENDING_TOTP_TIMEOUT, SessionError, SessionState};
use crate::throttle::{MAX_ATTEMPTS, record_attempt};
use crate::vault::{self, VaultError, VaultKey};

#[derive(Debug, Error)]
pub enum TotpVerifyError {
    #[error("database: {0}")]
    Database(#[from] sqlx::Error),
    #[error("session: {0}")]
    Session(#[from] SessionError),
    #[error("vault: {0}")]
    Vault(#[from] VaultError),
    #[error("the stored TOTP secret is not usable: {0}")]
    Secret(#[from] TotpError),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TotpOutcome {
    /// The session is now authenticated.
    Verified,
    /// No pending session, an expired one, a wrong code or a replayed code.
    Rejected,
    Throttled,
}

/// What the caller has: the pool, the vault key and the clock reading.
#[derive(Clone, Copy)]
pub struct Verifier<'a> {
    pub pool: &'a PgPool,
    pub key: &'a VaultKey,
    pub now: Instant,
}

/// The pending session and the code typed for it.
#[derive(Clone, Copy)]
struct Submission<'a> {
    live: &'a LiveSession,
    code: &'a str,
}

/// # Errors
/// Infrastructure failures only; a bad code is an `Ok(Rejected)`.
pub async fn verify_totp(
    verifier: Verifier<'_>,
    session_token: &str,
    code: &str,
) -> Result<TotpOutcome, TotpVerifyError> {
    let Some(live) = pending_session(&verifier, session_token).await? else {
        return Ok(TotpOutcome::Rejected);
    };
    let throttle_key = throttle_key(live.user_id);
    if record_attempt(verifier.pool, &throttle_key, verifier.now).await? > MAX_ATTEMPTS {
        return Ok(TotpOutcome::Throttled);
    }
    check_and_promote(&verifier, Submission { live: &live, code }).await
}

async fn pending_session(
    verifier: &Verifier<'_>,
    token: &str,
) -> Result<Option<LiveSession>, TotpVerifyError> {
    let live = session::lookup(verifier.pool, token, verifier.now).await?;
    let fresh = |live: &LiveSession| {
        live.state == SessionState::PendingTotp
            && live
                .created_at
                .checked_add(PENDING_TOTP_TIMEOUT)
                .is_some_and(|deadline| deadline > verifier.now)
    };
    Ok(live.filter(fresh))
}

// why: a hash key keeps user ids out of the throttle table's readable keys, like sign-in does.
fn throttle_key(user: Uuid) -> String {
    to_hex(&Sha256::digest(format!("totp:{user}").as_bytes()))
}

async fn check_and_promote(
    verifier: &Verifier<'_>,
    submission: Submission<'_>,
) -> Result<TotpOutcome, TotpVerifyError> {
    let live = submission.live;
    let mut transaction = verifier.pool.begin().await?;
    let accepted = check_code(&mut transaction, verifier, submission).await?;
    if accepted {
        session::promote(&mut transaction, live.id).await?;
    }
    let subject = UserId::from_uuid(live.user_id).to_string();
    audit::record(
        &mut transaction,
        audit_entry(verifier.now, &subject, accepted),
    )
    .await?;
    transaction.commit().await?;
    Ok(if accepted {
        TotpOutcome::Verified
    } else {
        TotpOutcome::Rejected
    })
}

/// Locks the TOTP row, checks the code and records the accepted step.
async fn check_code(
    connection: &mut PgConnection,
    verifier: &Verifier<'_>,
    submission: Submission<'_>,
) -> Result<bool, TotpVerifyError> {
    let Submission { live, code } = submission;
    let row = sqlx::query(
        "select secret_enc, last_accepted_step from totp
         where user_id = $1 and state = 'enabled' for update",
    )
    .bind(live.user_id)
    .fetch_optional(&mut *connection)
    .await?;
    let Some(row) = row else { return Ok(false) };
    let stored: Vec<u8> = row.try_get("secret_enc")?;
    let last: Option<i64> = row.try_get("last_accepted_step")?;
    let secret = TotpSecret::from_bytes(vault::open(verifier.key, live.user_id, &stored)?)?;
    let attempt = Attempt {
        code,
        now: verifier.now,
        last_accepted: last.and_then(|step| u64::try_from(step).ok()).map(TotpStep),
    };
    match verify_code(&secret, attempt) {
        Ok(step) => record_step(connection, live.user_id, step)
            .await
            .map(|()| true),
        Err(_) => Ok(false),
    }
}

async fn record_step(
    connection: &mut PgConnection,
    user: Uuid,
    step: TotpStep,
) -> Result<(), TotpVerifyError> {
    let step = i64::try_from(step.0).unwrap_or(i64::MAX);
    sqlx::query("update totp set last_accepted_step = $2 where user_id = $1")
        .bind(user)
        .bind(step)
        .execute(connection)
        .await?;
    Ok(())
}

fn audit_entry(at: Instant, subject: &str, accepted: bool) -> AuditEntry<'_> {
    AuditEntry {
        at,
        actor: subject,
        subject: Some(subject),
        action: if accepted {
            "totp_verified"
        } else {
            "totp_failed"
        },
        address: None,
    }
}
