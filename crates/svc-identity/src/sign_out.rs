//! Sign-out: revoke the session behind the cookie and audit it in the same transaction.

use contracts_ids::UserId;
use platform_time::Instant;
use sqlx::PgPool;

use crate::audit::{self, AuditEntry};
use crate::session::{self, SessionError};

/// Unknown and already revoked tokens do nothing and are not audited.
///
/// # Errors
/// Database failures.
pub async fn sign_out(pool: &PgPool, token: &str, now: Instant) -> Result<(), SessionError> {
    let mut transaction = pool.begin().await?;
    if let Some(user) = session::revoke(&mut transaction, token, now).await? {
        let subject = UserId::from_uuid(user).to_string();
        let entry = AuditEntry {
            at: now,
            actor: &subject,
            subject: Some(&subject),
            action: "sign_out",
            address: None,
        };
        audit::record(&mut transaction, entry).await?;
    }
    transaction.commit().await?;
    Ok(())
}
