//! Pulls `email.requested` events from identity into the outbox, one page per transaction.
//! The cursor moves only with the rows it covers, so a failed page is read again and the
//! `(source, event_id, kind)` key makes the second read a no-op.

use std::time::Duration;

use contracts_ids::UserId;
use platform_internal_http::{Caller, SignedCall};
use platform_random::{OsRandom, uuid_v7};
use platform_time::Instant;
use serde::Deserialize;
use serde_json::Value;
use sqlx::{PgConnection, PgPool};
use thiserror::Error;
use uuid::Uuid;

const PAGE_LIMIT: u32 = 100;
const MAX_PAGES: usize = 20;
const CALL_TIMEOUT: Duration = Duration::from_secs(5);
const EMAIL_EVENT: &str = "email.requested";
const KINDS: [&str; 3] = ["invite", "password_reset", "password_changed"];

/// The service events are pulled from.
#[derive(Debug, Clone, Copy)]
pub struct Source<'a> {
    /// The service name (`identity`): the callee of the signed call and the cursor key.
    pub name: &'a str,
    /// Its base URL, for example `http://identity:8080`.
    pub base: &'a str,
}

/// What a pull needs to reach the database and the source.
#[derive(Clone, Copy)]
pub struct Hub<'a> {
    pub pool: &'a PgPool,
    pub caller: &'a Caller,
}

/// The source name and the time of one pull, shared by every statement of the page.
#[derive(Clone, Copy)]
struct Scope<'a> {
    source: &'a str,
    now: Instant,
}

/// What one pull changed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PullReport {
    pub inserted: usize,
    pub cursor: i64,
}

/// Why a pull failed; nothing was changed.
#[derive(Debug, Error)]
pub enum PullError {
    #[error("the event source did not answer")]
    Unreachable,
    #[error("the event source answered with status {0}")]
    Status(u16),
    #[error("the event page could not be read")]
    Malformed,
    #[error("no identifier could be generated")]
    Random,
    #[error("the database failed")]
    Database(#[from] sqlx::Error),
}

#[derive(Deserialize)]
struct Page {
    events: Vec<Event>,
    next: i64,
}

#[derive(Deserialize)]
struct Event {
    id: String,
    #[serde(rename = "type")]
    kind: String,
    v: i64,
    payload: Value,
}

/// One outbox row to insert.
struct Pending<'a> {
    id: Uuid,
    event_id: Uuid,
    kind: &'a str,
    request_id: &'a str,
    user_id: Uuid,
    language: &'a str,
}

/// Reads one page after the stored cursor and stores its mail requests.
///
/// # Errors
/// [`PullError`] when the source fails or answers badly, or the database fails.
pub async fn pull_once(
    hub: Hub<'_>,
    source: Source<'_>,
    now: Instant,
) -> Result<PullReport, PullError> {
    let cursor = stored_cursor(hub.pool, source.name).await?;
    let page = fetch(hub.caller, source, (cursor, now)).await?;
    let scope = Scope {
        source: source.name,
        now,
    };
    store_page(hub.pool, scope, &page).await
}

/// Repeats [`pull_once`] until a page is empty or 20 pages were read; returns the total inserted.
///
/// # Errors
/// The first [`PullError`]; pages already stored stay stored.
pub async fn pull_all(hub: Hub<'_>, source: Source<'_>, now: Instant) -> Result<usize, PullError> {
    let mut total = 0;
    let mut pages = 0;
    let mut more = true;
    while more && pages < MAX_PAGES {
        let before = stored_cursor(hub.pool, source.name).await?;
        let report = pull_once(hub, source, now).await?;
        total += report.inserted;
        more = report.cursor > before;
        pages += 1;
    }
    Ok(total)
}

async fn stored_cursor(pool: &PgPool, source: &str) -> Result<i64, PullError> {
    let found: Option<i64> = sqlx::query_scalar("select cursor from cursors where source = $1")
        .bind(source)
        .fetch_optional(pool)
        .await?;
    Ok(found.unwrap_or(0))
}

async fn fetch(
    caller: &Caller,
    source: Source<'_>,
    (cursor, now): (i64, Instant),
) -> Result<Page, PullError> {
    let url = format!(
        "{}/internal/events?after={cursor}&limit={PAGE_LIMIT}",
        source.base.trim_end_matches('/')
    );
    let reply = caller
        .call(SignedCall {
            method: axum::http::Method::GET,
            url: &url,
            callee: source.name,
            timeout: CALL_TIMEOUT,
            now,
            body: None,
        })
        .await
        .map_err(|_| PullError::Unreachable)?;
    if reply.status.as_u16() != 200 {
        return Err(PullError::Status(reply.status.as_u16()));
    }
    serde_json::from_slice(&reply.body).map_err(|_| PullError::Malformed)
}

async fn store_page(pool: &PgPool, scope: Scope<'_>, page: &Page) -> Result<PullReport, PullError> {
    let mut transaction = pool.begin().await?;
    let mut inserted = 0;
    for event in &page.events {
        inserted += insert_event(&mut transaction, scope, event).await?;
    }
    let cursor = advance(&mut transaction, scope, page.next).await?;
    transaction.commit().await?;
    Ok(PullReport { inserted, cursor })
}

async fn insert_event(
    connection: &mut PgConnection,
    scope: Scope<'_>,
    event: &Event,
) -> Result<usize, PullError> {
    let Some(mail) = mail_request(event) else {
        return Ok(0);
    };
    let id = uuid_v7(scope.now.unix_millis(), &OsRandom).map_err(|_| PullError::Random)?;
    let row = Pending { id, ..mail };
    insert_row(connection, scope, &row).await
}

/// The mail request an event carries; `None` for other events and for payloads we cannot use.
fn mail_request(event: &Event) -> Option<Pending<'_>> {
    if event.kind != EMAIL_EVENT || event.v != 1 {
        return None;
    }
    let kind = KINDS
        .into_iter()
        .find(|kind| Some(*kind) == text(&event.payload, "kind"))?;
    let user_id = text(&event.payload, "user_id")?.parse::<UserId>().ok()?;
    Some(Pending {
        id: Uuid::nil(),
        event_id: Uuid::parse_str(&event.id).ok()?,
        kind,
        request_id: text(&event.payload, "request_id")?,
        user_id: user_id.as_uuid(),
        language: text(&event.payload, "language")?,
    })
}

fn text<'a>(payload: &'a Value, key: &str) -> Option<&'a str> {
    payload.get(key)?.as_str()
}

async fn insert_row(
    connection: &mut PgConnection,
    scope: Scope<'_>,
    row: &Pending<'_>,
) -> Result<usize, PullError> {
    let done = sqlx::query(
        "insert into outbox (id, source, event_id, kind, request_id, user_id, language, state,
                             attempts, next_attempt_at, created_at, updated_at)
         values ($1::uuid, $2, $3::uuid, $4, $5, $6::uuid, $7, 'queued', 0, to_timestamp($8), to_timestamp($8),
                 to_timestamp($8))
         on conflict (source, event_id, kind) do nothing",
    )
    .bind(row.id.to_string())
    .bind(scope.source)
    .bind(row.event_id.to_string())
    .bind(row.kind)
    .bind(row.request_id)
    .bind(row.user_id.to_string())
    .bind(row.language)
    .bind(scope.now.unix_seconds())
    .execute(connection)
    .await?;
    Ok(usize::try_from(done.rows_affected()).unwrap_or(0))
}

/// Stores the cursor, never moving it backwards; returns the stored value.
async fn advance(
    connection: &mut PgConnection,
    scope: Scope<'_>,
    next: i64,
) -> Result<i64, PullError> {
    let stored: i64 = sqlx::query_scalar(
        "insert into cursors (source, cursor, updated_at) values ($1, greatest($2, 0), to_timestamp($3))
         on conflict (source) do update
             set cursor = greatest(cursors.cursor, excluded.cursor), updated_at = excluded.updated_at
         returning cursor",
    )
    .bind(scope.source)
    .bind(next)
    .bind(scope.now.unix_seconds())
    .fetch_one(connection)
    .await?;
    Ok(stored)
}
