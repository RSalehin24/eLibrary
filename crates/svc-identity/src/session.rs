//! Server-side sessions: an opaque random token in an `HttpOnly` cookie, only its SHA-256 stored
//! (REQ-IDN-007). Idle and absolute expiry are checked on every lookup.

use std::time::Duration;

use platform_random::{RandomError, RandomSource, random_hex};
use platform_time::Instant;
use sha2::{Digest, Sha256};
use sqlx::{PgConnection, PgPool, Row};
use thiserror::Error;
use uuid::Uuid;

pub const IDLE_TIMEOUT: Duration = Duration::from_hours(12);
pub const ABSOLUTE_TIMEOUT: Duration = Duration::from_hours(720);
const TOKEN_BYTES: usize = 32;

#[derive(Debug, Error)]
pub enum SessionError {
    #[error("database: {0}")]
    Database(#[from] sqlx::Error),
    #[error("randomness: {0}")]
    Random(#[from] RandomError),
    #[error("session lifetime out of range")]
    TimeRange,
    #[error("stored session state is not recognised")]
    UnknownState,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionState {
    PendingTotp,
    Authenticated,
}

impl SessionState {
    fn as_stored(self) -> &'static str {
        match self {
            Self::PendingTotp => "pending_totp",
            Self::Authenticated => "authenticated",
        }
    }

    fn from_stored(text: &str) -> Option<Self> {
        [Self::PendingTotp, Self::Authenticated]
            .into_iter()
            .find(|state| state.as_stored() == text)
    }
}

/// What the caller hands to the browser; the clear token exists only here, never in the database.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IssuedSession {
    pub token: String,
    pub csrf_token: String,
    pub state: SessionState,
    pub expires_at: Instant,
}

pub(crate) struct NewSession<'a, R: RandomSource> {
    pub id: Uuid,
    pub user_id: Uuid,
    pub state: SessionState,
    pub now: Instant,
    pub random: &'a R,
}

pub(crate) fn hash_token(token: &str) -> Vec<u8> {
    Sha256::digest(token.as_bytes()).to_vec()
}

pub(crate) async fn create<R: RandomSource>(
    connection: &mut PgConnection,
    new: NewSession<'_, R>,
) -> Result<IssuedSession, SessionError> {
    let token = random_hex(new.random, TOKEN_BYTES)?;
    let csrf_token = random_hex(new.random, TOKEN_BYTES)?;
    let expires_at = new
        .now
        .checked_add(ABSOLUTE_TIMEOUT)
        .ok_or(SessionError::TimeRange)?;
    sqlx::query(
        "insert into sessions (id, token_hash, user_id, state, csrf_hash, created_at, last_seen_at, expires_at)
         values ($1, $2, $3, $4, $5, $6, $6, $7)",
    )
    .bind(new.id)
    .bind(hash_token(&token))
    .bind(new.user_id)
    .bind(new.state.as_stored())
    .bind(hash_token(&csrf_token))
    .bind(new.now.to_offset_date_time())
    .bind(expires_at.to_offset_date_time())
    .execute(connection)
    .await?;
    Ok(IssuedSession {
        token,
        csrf_token,
        state: new.state,
        expires_at,
    })
}

/// A session that is neither revoked nor expired.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LiveSession {
    pub id: Uuid,
    pub user_id: Uuid,
    pub state: SessionState,
}

/// Finds the session for a cookie value and slides the idle window. `None` for unknown, revoked,
/// idle-expired and absolute-expired sessions alike.
///
/// # Errors
/// Database failures.
pub async fn lookup(
    pool: &PgPool,
    token: &str,
    now: Instant,
) -> Result<Option<LiveSession>, SessionError> {
    let row = sqlx::query(
        "update sessions set last_seen_at = $2
         where token_hash = $1 and revoked_at is null and expires_at > $2
           and last_seen_at + make_interval(secs => $3) > $2
         returning id, user_id, state",
    )
    .bind(hash_token(token))
    .bind(now.to_offset_date_time())
    .bind(IDLE_TIMEOUT.as_secs_f64())
    .fetch_optional(pool)
    .await?;
    row.as_ref().map(live_from).transpose()
}

fn live_from(row: &sqlx::postgres::PgRow) -> Result<LiveSession, SessionError> {
    let state: String = row.try_get("state")?;
    Ok(LiveSession {
        id: row.try_get("id")?,
        user_id: row.try_get("user_id")?,
        state: SessionState::from_stored(&state).ok_or(SessionError::UnknownState)?,
    })
}

/// Revokes the session behind a cookie value (sign-out). Unknown tokens are a no-op.
///
/// # Errors
/// Database failures.
pub async fn revoke(pool: &PgPool, token: &str, now: Instant) -> Result<(), SessionError> {
    sqlx::query("update sessions set revoked_at = $2 where token_hash = $1 and revoked_at is null")
        .bind(hash_token(token))
        .bind(now.to_offset_date_time())
        .execute(pool)
        .await?;
    Ok(())
}
