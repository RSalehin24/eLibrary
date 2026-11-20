//! Invite and reset links (REQ-IDN-002, INV-IDN-002). Only the SHA-256 of a token is stored for
//! lookup; the token itself is sealed into the mail request so notify can fetch it by reference
//! (once) and nothing readable sits in events or logs.

use platform_random::{OsRandom, RandomError, RandomSource, to_hex, uuid_v7};
use sha2::{Digest, Sha256};
use sqlx::PgConnection;
use std::time::Duration;

use crate::admin_change::{ChangeError, Outgoing, Request, emit_with};
use crate::vault::{Plain, VaultError, VaultKey, seal};

const TOKEN_BYTES: usize = 48;
const NONCE_BYTES: usize = 16;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Purpose {
    Invite,
    Reset,
}

impl Purpose {
    pub(crate) fn as_str(self) -> &'static str {
        match self {
            Self::Invite => "invite",
            Self::Reset => "reset",
        }
    }

    /// The mail kind announced for this purpose.
    fn mail_kind(self) -> &'static str {
        match self {
            Self::Invite => "invite",
            Self::Reset => "password_reset",
        }
    }

    /// Invite 7 days, reset 24 hours.
    fn lifetime(self) -> Duration {
        match self {
            Self::Invite => Duration::from_hours(168),
            Self::Reset => Duration::from_hours(24),
        }
    }
}

#[derive(Debug, thiserror::Error)]
pub(crate) enum LinkError {
    #[error("database: {0}")]
    Database(#[from] sqlx::Error),
    #[error("randomness: {0}")]
    Random(#[from] RandomError),
    #[error("vault: {0}")]
    Vault(#[from] VaultError),
    #[error("change: {0}")]
    Change(#[from] ChangeError),
    #[error("password hashing did not finish")]
    HashTask,
}

/// Who is mailed what: the request (its `target` is the mailed user), the purpose and language.
#[derive(Clone, Copy)]
pub(crate) struct Issue<'a> {
    pub request: Request<'a>,
    pub purpose: Purpose,
    pub language: &'a str,
}

/// The hash a link token is looked up by.
pub(crate) fn token_hash(token: &str) -> Vec<u8> {
    Sha256::digest(token.as_bytes()).to_vec()
}

/// A fresh token with its row ids, as generated for one link.
struct Fresh {
    bytes: [u8; TOKEN_BYTES],
    token: String,
    request_id: String,
}

fn fresh(request: Request<'_>) -> Result<Fresh, RandomError> {
    let mut bytes = [0_u8; TOKEN_BYTES];
    OsRandom.fill(&mut bytes)?;
    Ok(Fresh {
        token: to_hex(&bytes),
        bytes,
        request_id: uuid_v7(request.now.unix_millis(), &OsRandom)?.to_string(),
    })
}

async fn store_link(
    connection: &mut PgConnection,
    issue: Issue<'_>,
    fresh: &Fresh,
) -> Result<(), LinkError> {
    let Issue {
        request, purpose, ..
    } = issue;
    let expires = request
        .now
        .checked_add(purpose.lifetime())
        .ok_or(RandomError)?;
    sqlx::query(
        "insert into links (id, user_id, purpose, token_hash, nonce, state, expires_at, request_id, created_at)
         values ($1, $2, $3, $4, $5, 'issued', $6, $7, $8)",
    )
    .bind(uuid_v7(request.now.unix_millis(), &OsRandom)?)
    .bind(request.target)
    .bind(purpose.as_str())
    .bind(token_hash(&fresh.token))
    .bind(fresh.bytes.get(..NONCE_BYTES))
    .bind(expires.to_offset_date_time())
    .bind(&fresh.request_id)
    .bind(request.now.to_offset_date_time())
    .execute(connection)
    .await?;
    Ok(())
}

/// Queues the mail request holding the sealed token and announces it.
async fn queue_mail(
    connection: &mut PgConnection,
    key: &VaultKey,
    mail: (Issue<'_>, &Fresh),
) -> Result<(), LinkError> {
    let (issue, fresh) = mail;
    let Issue {
        request,
        purpose,
        language,
    } = issue;
    let user = request.target;
    let plain = Plain {
        owner: user,
        bytes: fresh.token.as_bytes(),
    };
    let sealed = seal(key, plain, &OsRandom)?;
    sqlx::query(
        "insert into email_requests (request_id, kind, user_id, language, link_ref, created_at)
         values ($1, $2, $3, $4, $5, $6)",
    )
    .bind(&fresh.request_id)
    .bind(purpose.mail_kind())
    .bind(user)
    .bind(language)
    .bind(to_hex(&sealed))
    .bind(request.now.to_offset_date_time())
    .execute(&mut *connection)
    .await?;
    announce(connection, issue, fresh).await
}

/// The `email.requested` event: ids and kind only, never the address or the link.
async fn announce(
    connection: &mut PgConnection,
    issue: Issue<'_>,
    fresh: &Fresh,
) -> Result<(), LinkError> {
    let Issue {
        request,
        purpose,
        language,
    } = issue;
    let payload = serde_json::json!({
        "request_id": fresh.request_id,
        "kind": purpose.mail_kind(),
        "user_id": contracts_ids::UserId::from_uuid(request.target).to_string(),
        "language": language,
    });
    let event = Outgoing {
        kind: "email.requested",
        payload,
    };
    emit_with(connection, request, event).await?;
    Ok(())
}

/// Supersedes the user's issued link of this purpose, stores a new one and queues the mail
/// request with an `email.requested` event, all in the caller's transaction.
pub(crate) async fn issue(
    connection: &mut PgConnection,
    key: &VaultKey,
    issue: Issue<'_>,
) -> Result<(), LinkError> {
    sqlx::query(
        "update links set state = 'superseded' where user_id = $1 and purpose = $2 and state = 'issued'",
    )
    .bind(issue.request.target)
    .bind(issue.purpose.as_str())
    .execute(&mut *connection)
    .await?;
    let fresh = fresh(issue.request)?;
    store_link(connection, issue, &fresh).await?;
    queue_mail(connection, key, (issue, &fresh)).await
}

/// True when the token starts with the hex of the nonce stored with the link.
pub(crate) fn nonce_matches(token: &str, nonce: &[u8]) -> bool {
    token.starts_with(&to_hex(nonce))
}
