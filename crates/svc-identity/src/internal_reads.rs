//! Service-to-service reads (identity contract, internal routes): user info for notify and
//! catalog, the grant version for access, the event feed, and the one-time mail request.

use platform_config::PublicOrigin;
use platform_time::Instant;
use serde::Serialize;
use sqlx::{PgPool, Row};

use crate::vault::{self, VaultError, VaultKey};

const MAX_PAGE: i64 = 500;

#[derive(Debug, thiserror::Error)]
pub enum ReadError {
    #[error("database: {0}")]
    Database(#[from] sqlx::Error),
    #[error("vault: {0}")]
    Vault(#[from] VaultError),
    #[error("stored data is malformed")]
    Malformed,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct UserInfo {
    pub status: String,
    pub language: String,
    pub kindle_addresses: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct EventRecord {
    pub cursor: i64,
    pub id: String,
    #[serde(rename = "type")]
    pub kind: String,
    pub v: i32,
    pub subject_id: Option<String>,
    pub request_id: Option<String>,
    pub payload: serde_json::Value,
    pub at: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct EventPage {
    pub events: Vec<EventRecord>,
    pub next: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct EmailRequest {
    pub kind: String,
    pub to: String,
    pub language: String,
    pub link: String,
}

/// # Errors
/// Database failure.
pub async fn user_info(pool: &PgPool, id: uuid::Uuid) -> Result<Option<UserInfo>, ReadError> {
    let row = sqlx::query("select status, language from users where id = $1")
        .bind(id)
        .fetch_optional(pool)
        .await?;
    let Some(row) = row else {
        return Ok(None);
    };
    let addresses = sqlx::query_scalar::<_, String>(
        "select address from kindle_addresses where user_id = $1 order by position",
    )
    .bind(id)
    .fetch_all(pool)
    .await?;
    Ok(Some(UserInfo {
        status: row.try_get("status")?,
        language: row.try_get("language")?,
        kindle_addresses: addresses,
    }))
}

/// # Errors
/// Database failure.
pub async fn grant_version(pool: &PgPool, id: uuid::Uuid) -> Result<Option<i64>, ReadError> {
    Ok(
        sqlx::query_scalar::<_, i64>("select grant_version from users where id = $1")
            .bind(id)
            .fetch_optional(pool)
            .await?,
    )
}

fn event_record(row: &sqlx::postgres::PgRow) -> Result<EventRecord, ReadError> {
    let payload: String = row.try_get("payload")?;
    let subject: Option<String> = row.try_get("subject_id")?;
    Ok(EventRecord {
        cursor: row.try_get("cursor")?,
        id: row.try_get("id")?,
        kind: row.try_get("type")?,
        v: row.try_get("v")?,
        subject_id: subject,
        request_id: row.try_get("request_id")?,
        payload: serde_json::from_str(&payload).map_err(|_| ReadError::Malformed)?,
        at: row.try_get("at")?,
    })
}

/// Events with a cursor greater than `after`, ascending; `limit` is clamped to 1..=500.
///
/// # Errors
/// Database failure.
pub async fn events_after(pool: &PgPool, after: i64, limit: i64) -> Result<EventPage, ReadError> {
    let rows = sqlx::query(
        "select cursor, id::text as id, type, v, subject_id::text as subject_id, request_id,
                payload::text as payload, extract(epoch from at)::bigint as at
         from events where cursor > $1 order by cursor limit $2",
    )
    .bind(after)
    .bind(limit.clamp(1, MAX_PAGE))
    .fetch_all(pool)
    .await?;
    let events = rows
        .iter()
        .map(event_record)
        .collect::<Result<Vec<_>, _>>()?;
    let next = events.last().map_or(after, |event| event.cursor);
    Ok(EventPage { events, next })
}

fn from_hex(text: &str) -> Option<Vec<u8>> {
    if !text.len().is_multiple_of(2) {
        return None;
    }
    text.as_bytes()
        .chunks(2)
        .map(|pair| {
            let pair = std::str::from_utf8(pair).ok()?;
            u8::from_str_radix(pair, 16).ok()
        })
        .collect()
}

fn link_path(kind: &str, token: &str) -> Result<String, ReadError> {
    match kind {
        "invite" => Ok(format!("/accept-invite?token={token}")),
        "password_reset" => Ok(format!("/reset-password?token={token}")),
        _ => Err(ReadError::Malformed),
    }
}

/// What reading a mail request needs besides the request itself.
#[derive(Clone, Copy)]
pub struct MailContext<'a> {
    pub pool: &'a PgPool,
    pub key: &'a VaultKey,
    pub origin: &'a PublicOrigin,
}

fn open_link(
    key: &VaultKey,
    origin: &PublicOrigin,
    row: &sqlx::postgres::PgRow,
) -> Result<Option<String>, ReadError> {
    let link_ref: String = row.try_get("link_ref")?;
    if link_ref.is_empty() {
        return Ok(None);
    }
    let user: uuid::Uuid = row.try_get("user_id")?;
    let sealed = from_hex(&link_ref).ok_or(ReadError::Malformed)?;
    let token =
        String::from_utf8(vault::open(key, user, &sealed)?).map_err(|_| ReadError::Malformed)?;
    let kind: String = row.try_get("kind")?;
    Ok(Some(origin.url(&link_path(&kind, &token)?)))
}

async fn fetch_request(
    transaction: &mut sqlx::PgTransaction<'_>,
    request_id: &str,
    now: Instant,
) -> Result<Option<sqlx::postgres::PgRow>, ReadError> {
    Ok(sqlx::query(
        "select r.kind, r.language, r.link_ref, r.user_id, u.email
         from email_requests r
         join users u on u.id = r.user_id
         join links l on l.request_id = r.request_id
         where r.request_id = $1 and l.state = 'issued' and l.expires_at > $2
         for update of r",
    )
    .bind(request_id)
    .bind(now.to_offset_date_time())
    .fetch_optional(&mut **transaction)
    .await?)
}

/// Everything needed to mail one request; `None` when it is gone, already read, or its link is
/// no longer issued or has expired. The sealed token is wiped in the same transaction.
///
/// # Errors
/// Database failure, or a stored token that cannot be opened.
pub async fn email_request(
    context: MailContext<'_>,
    request_id: &str,
    now: Instant,
) -> Result<Option<EmailRequest>, ReadError> {
    let mut transaction = context.pool.begin().await?;
    let row = fetch_request(&mut transaction, request_id, now).await?;
    let Some(row) = row else {
        return Ok(None);
    };
    let Some(link) = open_link(context.key, context.origin, &row)? else {
        return Ok(None);
    };
    sqlx::query("update email_requests set link_ref = '' where request_id = $1")
        .bind(request_id)
        .execute(&mut *transaction)
        .await?;
    transaction.commit().await?;
    Ok(Some(EmailRequest {
        kind: row.try_get("kind")?,
        to: row.try_get("email")?,
        language: row.try_get("language")?,
        link,
    }))
}
