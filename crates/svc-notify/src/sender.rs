//! Sends due mails from the outbox (REQ-NTF-002, 008, 010). A row is claimed with a lease, its
//! content is fetched from identity by reference, rendered, sent, and the result is written
//! together with one delivery-log row. Addresses and links live only in memory.

use std::time::Duration;

use axum::http::{Method, StatusCode};
use platform_internal_http::{Caller, SignedCall};
use platform_time::Instant;
use sqlx::PgPool;

use crate::render::{MailRequest, render};
use crate::retry::{Step, next_step};
use crate::transport::{MailTransport, SendError};

const BATCH: i64 = 10;
const CALL_TIMEOUT: Duration = Duration::from_secs(5);

/// What the sender needs.
pub struct Deps<'a, T: MailTransport> {
    pub pool: &'a PgPool,
    pub caller: &'a Caller,
    pub identity_base: &'a str,
    pub transport: &'a T,
}

/// Why a sender pass could not run; carries no mail data.
#[derive(Debug, thiserror::Error)]
pub enum SendLoopError {
    #[error("database error")]
    Database(#[from] sqlx::Error),
}

/// One claimed outbox row.
struct Claimed {
    id: String,
    request_id: String,
    attempts: i32,
}

/// The result of one attempt, with the masked address when it was learned.
struct Attempt {
    result: Result<(), SendError>,
    masked: Option<String>,
}

/// What to write after an attempt.
struct Settle {
    id: String,
    attempt: i32,
    state: &'static str,
    status: &'static str,
    class: Option<&'static str>,
    masked: Option<String>,
    next_ms: i64,
    at_ms: i64,
}

/// Claims up to ten due rows and handles each. Returns how many rows were handled.
///
/// # Errors
/// [`SendLoopError::Database`] when the claim or a result write fails; rows left in
/// `sending` are picked up again when their lease expires.
pub async fn send_due<T: MailTransport>(
    deps: &Deps<'_, T>,
    now: Instant,
) -> Result<usize, SendLoopError> {
    let rows = claim(deps.pool, now).await?;
    for row in &rows {
        handle(deps, now, row).await?;
    }
    Ok(rows.len())
}

fn millis(at: Instant) -> i64 {
    i64::try_from(at.unix_millis()).unwrap_or(i64::MAX)
}

async fn claim(pool: &PgPool, now: Instant) -> Result<Vec<Claimed>, sqlx::Error> {
    let rows = sqlx::query_as::<_, (String, String, i32)>(
        "with t as (select to_timestamp($1::bigint / 1000.0) as now),
         due as (
             select o.id from outbox o, t
             where (o.state = 'queued' and o.next_attempt_at <= t.now)
                or (o.state = 'sending' and o.lease_until < t.now)
             order by o.next_attempt_at
             limit $2
             for update of o skip locked)
         update outbox o
            set state = 'sending', lease_until = t.now + interval '5 minutes', updated_at = t.now
           from due, t
          where o.id = due.id
         returning o.id::text, o.request_id, o.attempts",
    )
    .bind(millis(now))
    .bind(BATCH)
    .fetch_all(pool)
    .await?;
    Ok(rows
        .into_iter()
        .map(|(id, request_id, attempts)| Claimed {
            id,
            request_id,
            attempts,
        })
        .collect())
}

async fn handle<T: MailTransport>(
    deps: &Deps<'_, T>,
    now: Instant,
    row: &Claimed,
) -> Result<(), sqlx::Error> {
    let attempt = deliver(deps, now, &row.request_id).await;
    write(deps.pool, &settle_for(row, now, &attempt)).await
}

async fn deliver<T: MailTransport>(deps: &Deps<'_, T>, now: Instant, request_id: &str) -> Attempt {
    let request = match fetch(deps, now, request_id).await {
        Ok(request) => request,
        Err(error) => {
            return Attempt {
                result: Err(error),
                masked: None,
            };
        }
    };
    let masked = Some(mask(&request.to));
    let result = match render(&request) {
        Some(mail) => deps.transport.send(&mail).await,
        None => Err(SendError::Permanent),
    };
    Attempt { result, masked }
}

fn safe_reference(request_id: &str) -> bool {
    !request_id.is_empty()
        && request_id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
}

async fn fetch<T: MailTransport>(
    deps: &Deps<'_, T>,
    now: Instant,
    request_id: &str,
) -> Result<MailRequest, SendError> {
    if !safe_reference(request_id) {
        return Err(SendError::Permanent);
    }
    let url = format!(
        "{}/internal/email-requests/{request_id}",
        deps.identity_base
    );
    let call = SignedCall {
        method: Method::GET,
        url: &url,
        callee: "identity",
        timeout: CALL_TIMEOUT,
        now,
        body: None,
    };
    let reply = deps
        .caller
        .call(call)
        .await
        .map_err(|_| SendError::Retryable)?;
    match reply.status {
        StatusCode::OK => serde_json::from_slice(&reply.body).map_err(|_| SendError::Permanent),
        StatusCode::NOT_FOUND | StatusCode::GONE => Err(SendError::Permanent),
        _ => Err(SendError::Retryable),
    }
}

/// `a***@example.org` from `alice@example.org`; `***` when there is no domain.
fn mask(address: &str) -> String {
    match address.split_once('@') {
        Some((local, domain)) => {
            let first: String = local.chars().take(1).collect();
            format!("{first}***@{domain}")
        }
        None => "***".to_owned(),
    }
}

fn class_name(error: SendError) -> &'static str {
    match error {
        SendError::Retryable => "retryable",
        SendError::Permanent => "permanent",
    }
}

fn settle_for(row: &Claimed, now: Instant, attempt: &Attempt) -> Settle {
    let number = row.attempts.saturating_add(1);
    let at_ms = millis(now);
    let base = Settle {
        id: row.id.clone(),
        attempt: number,
        state: "sent",
        status: "sent",
        class: None,
        masked: attempt.masked.clone(),
        next_ms: at_ms,
        at_ms,
    };
    let Err(error) = attempt.result else {
        return base;
    };
    match next_step(number, error) {
        Step::RetryAfter(delay) => Settle {
            state: "queued",
            status: "retry",
            class: Some("retryable"),
            next_ms: millis(now.checked_add(delay).unwrap_or(now)),
            ..base
        },
        Step::Fail => Settle {
            state: "failed",
            status: "failed",
            class: Some(class_name(error)),
            ..base
        },
    }
}

async fn write(pool: &PgPool, settle: &Settle) -> Result<(), sqlx::Error> {
    let mut tx = pool.begin().await?;
    sqlx::query(
        "update outbox
            set state = $2, attempts = $3, next_attempt_at = to_timestamp($4::bigint / 1000.0),
                lease_until = null, error_class = $5, updated_at = to_timestamp($6::bigint / 1000.0)
          where id = $1::uuid",
    )
    .bind(&settle.id)
    .bind(settle.state)
    .bind(settle.attempt)
    .bind(settle.next_ms)
    .bind(settle.class)
    .bind(settle.at_ms)
    .execute(&mut *tx)
    .await?;
    sqlx::query(
        "insert into delivery_log (outbox_id, attempt, status, error_class, masked_address, at)
         values ($1::uuid, $2, $3, $4, $5, to_timestamp($6::bigint / 1000.0))",
    )
    .bind(&settle.id)
    .bind(settle.attempt)
    .bind(settle.status)
    .bind(settle.class)
    .bind(&settle.masked)
    .bind(settle.at_ms)
    .execute(&mut *tx)
    .await?;
    tx.commit().await
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn masks_keep_one_letter_and_the_domain() {
        assert_eq!(mask("alice@example.org"), "a***@example.org");
        assert_eq!(mask("বাংলা@example.org"), "ব***@example.org");
        assert_eq!(mask("nonsense"), "***");
    }

    #[test]
    fn references_are_plain_tokens() {
        assert!(safe_reference("0190-abc_DEF"));
        assert!(!safe_reference(""));
        assert!(!safe_reference("../x?y"));
    }
}
