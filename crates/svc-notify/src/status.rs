//! What other services may ask notify (internal, service token): the state of one message and
//! the outbox figures. Addresses appear only masked.

use serde::Serialize;
use sqlx::{PgPool, Row};
use uuid::Uuid;

#[derive(Debug, Serialize)]
pub struct MessageStatus {
    pub status: String,
    pub error_class: Option<String>,
    pub masked_address: Option<String>,
    pub attempts: i32,
}

/// The reported status of one outbox row, or `None` when there is no such message.
///
/// # Errors
/// Database failures.
pub async fn message(pool: &PgPool, id: Uuid) -> Result<Option<MessageStatus>, sqlx::Error> {
    let row = sqlx::query(
        "select o.state, o.error_class, o.attempts,
                (select l.masked_address from delivery_log l where l.outbox_id = o.id
                 order by l.attempt desc limit 1) as masked_address
         from outbox o where o.id = $1",
    )
    .bind(id)
    .fetch_optional(pool)
    .await?;
    row.map(|row| {
        let state: String = row.try_get("state")?;
        Ok(MessageStatus {
            status: state,
            error_class: row.try_get("error_class")?,
            masked_address: row.try_get("masked_address")?,
            attempts: row.try_get("attempts")?,
        })
    })
    .transpose()
}

#[derive(Debug, Serialize)]
pub struct Stats {
    pub queued: i64,
    pub sending: i64,
    pub failed: i64,
    pub oldest_queued_age_seconds: Option<i64>,
}

/// Outbox depth, age and failures (the metrics source).
///
/// # Errors
/// Database failures.
pub async fn stats(pool: &PgPool) -> Result<Stats, sqlx::Error> {
    let row = sqlx::query(
        "select count(*) filter (where state = 'queued') as queued,
                count(*) filter (where state = 'sending') as sending,
                count(*) filter (where state = 'failed') as failed,
                extract(epoch from (now() - min(created_at) filter (where state = 'queued')))::bigint as oldest
         from outbox",
    )
    .fetch_one(pool)
    .await?;
    Ok(Stats {
        queued: row.try_get("queued")?,
        sending: row.try_get("sending")?,
        failed: row.try_get("failed")?,
        oldest_queued_age_seconds: row.try_get("oldest")?,
    })
}
