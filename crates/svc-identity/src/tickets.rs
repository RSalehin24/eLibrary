//! Reading tickets (REQ-IDN-020..022, D-37): minted after the read decision, verified by the
//! reader on every use. Only the SHA-256 of the ticket is stored; read-once is consumed only by
//! a verify that asks to redeem.

use std::time::Duration;

use contracts_http::Scope;
use contracts_ids::{BookId, TicketId};
use domain_access::{
    AccountStatus, BookFacts, Decision, DecisionInput, DenyReason, Grant, ReadOnceStatus, Role,
    Subject, UserFacts, decide,
};
use platform_random::{OsRandom, RandomError, random_hex, uuid_v7};
use platform_time::Instant;
use sqlx::{PgConnection, PgPool, Row};
use thiserror::Error;
use uuid::Uuid;

use crate::session::hash_token;

/// How long a ticket lives (the table check allows at most this).
pub const TICKET_LIFETIME: Duration = Duration::from_mins(15);
const TOKEN_BYTES: usize = 32;

#[derive(Debug, Error)]
pub enum TicketError {
    #[error("database: {0}")]
    Database(#[from] sqlx::Error),
    #[error("randomness: {0}")]
    Random(#[from] RandomError),
    #[error("ticket lifetime out of range")]
    TimeRange,
}

/// Who asks to read which version of which book.
#[derive(Debug, Clone, Copy, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MintRequest {
    pub user_id: Uuid,
    pub book_id: Uuid,
    pub version_id: Uuid,
}

/// The clear ticket exists only in this value, never in the database.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct MintedTicket {
    pub ticket: String,
    pub ticket_id: Uuid,
    /// Unix seconds.
    pub expires_at: i64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MintOutcome {
    Minted(MintedTicket),
    Denied(DenyReason),
}

#[derive(Debug, Clone, Copy)]
pub struct VerifyRequest<'a> {
    pub ticket_id: Uuid,
    pub ticket: &'a str,
    pub book_id: Uuid,
    pub version_id: Uuid,
    pub redeem: bool,
}

/// Why a ticket was refused; every unknown or mismatching case is `Invalid`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TicketDenial {
    Invalid,
    Expired,
    ReadOnceConsumed,
}

impl TicketDenial {
    /// The wire code of the contract.
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Invalid => "ticket_invalid",
            Self::Expired => "ticket_expired",
            Self::ReadOnceConsumed => "read_once_consumed",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VerifyOutcome {
    Valid { user_id: Uuid },
    Denied(TicketDenial),
}

/// How the user may read the book.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Access {
    Denied(DenyReason),
    Normal,
    ReadOnce,
}

struct AccessQuery {
    user_id: Uuid,
    book_id: Uuid,
    ticket: Option<Uuid>,
    now: Instant,
}

fn role_of(name: &str) -> Option<Role> {
    match name {
        "reader" => Some(Role::Reader),
        "operator" => Some(Role::Operator),
        "admin" => Some(Role::Admin),
        _ => None,
    }
}

fn status_of(name: &str) -> Option<AccountStatus> {
    match name {
        "invited" => Some(AccountStatus::Invited),
        "active" => Some(AccountStatus::Active),
        "suspended" => Some(AccountStatus::Suspended),
        "disabled" => Some(AccountStatus::Disabled),
        _ => None,
    }
}

async fn load_user(
    connection: &mut PgConnection,
    user_id: Uuid,
) -> Result<Option<UserFacts>, sqlx::Error> {
    let Some(row) = sqlx::query("select status, role from users where id = $1")
        .bind(user_id)
        .fetch_optional(connection)
        .await?
    else {
        return Ok(None);
    };
    let status: String = row.try_get("status")?;
    let role: String = row.try_get("role")?;
    Ok(status_of(&status)
        .zip(role_of(&role))
        .map(|(status, role)| UserFacts {
            status,
            role,
            mfa_satisfied: true,
        }))
}

async fn load_grants(
    connection: &mut PgConnection,
    query: &AccessQuery,
) -> Result<Vec<Grant>, sqlx::Error> {
    let rows = sqlx::query(
        "select scope, book_id, expires_at from grants
         where user_id = $1 and active and (book_id is null or book_id = $2)",
    )
    .bind(query.user_id)
    .bind(query.book_id)
    .fetch_all(connection)
    .await?;
    let mut grants = Vec::new();
    for row in rows {
        grants.extend(grant_of(&row)?);
    }
    Ok(grants)
}

fn grant_of(row: &sqlx::postgres::PgRow) -> Result<Option<Grant>, sqlx::Error> {
    let name: String = row.try_get("scope")?;
    let book: Option<Uuid> = row.try_get("book_id")?;
    let expiry: Option<_> = row.try_get("expires_at")?;
    Ok(Scope::ALL
        .into_iter()
        .find(|scope| scope.as_str() == name)
        .map(|scope| Grant {
            scope,
            book: book.map(BookId::from_uuid),
            expires_at: expiry.map(Instant::from_offset_date_time),
            revoked: false,
        }))
}

async fn read_once_holder(
    connection: &mut PgConnection,
    query: &AccessQuery,
) -> Result<ReadOnceStatus, sqlx::Error> {
    let holder: Option<Uuid> = sqlx::query_scalar(
        "select ticket_id from read_once_uses where user_id = $1 and book_id = $2",
    )
    .bind(query.user_id)
    .bind(query.book_id)
    .fetch_optional(connection)
    .await?;
    Ok(holder.map_or(ReadOnceStatus::Unused, |id| {
        ReadOnceStatus::ConsumedBy(TicketId::from_uuid(id))
    }))
}

fn decision_for(
    scope: Scope,
    facts: (UserFacts, &[Grant], ReadOnceStatus),
    query: &AccessQuery,
) -> Decision {
    let (user, grants, read_once) = facts;
    decide(&DecisionInput {
        subject: Subject::User(user),
        scope,
        book: Some(BookFacts {
            id: BookId::from_uuid(query.book_id),
            published: true,
            deleted: false,
        }),
        grants,
        now: query.now,
        read_once,
        ticket: query.ticket.map(TicketId::from_uuid),
    })
}

/// A live `read_once` grant limits reading of the book to one opening (roles always hold plain
/// `read`, so the grant is what marks a book read-once); otherwise plain `read` decides.
async fn access(connection: &mut PgConnection, query: &AccessQuery) -> Result<Access, sqlx::Error> {
    let Some(user) = load_user(connection, query.user_id).await? else {
        return Ok(Access::Denied(DenyReason::AccountInactive));
    };
    let grants = load_grants(connection, query).await?;
    let spent = read_once_holder(connection, query).await?;
    let once = decision_for(Scope::ReadOnce, (user, &grants, spent), query);
    let plain = decision_for(Scope::Read, (user, &grants, spent), query);
    Ok(match (once, plain) {
        (Decision::Allow, _) => Access::ReadOnce,
        (Decision::Deny(DenyReason::ReadOnceConsumed), _) => {
            Access::Denied(DenyReason::ReadOnceConsumed)
        }
        (Decision::Deny(_), Decision::Allow) => Access::Normal,
        (Decision::Deny(_), Decision::Deny(reason)) => Access::Denied(reason),
    })
}

/// Mints a ticket when the user may read the book; read-once is not consumed.
///
/// # Errors
/// [`TicketError`] on database, randomness or time-range failure.
pub async fn mint(
    pool: &PgPool,
    request: MintRequest,
    now: Instant,
) -> Result<MintOutcome, TicketError> {
    let mut transaction = pool.begin().await?;
    let query = AccessQuery {
        user_id: request.user_id,
        book_id: request.book_id,
        ticket: None,
        now,
    };
    if let Access::Denied(reason) = access(&mut transaction, &query).await? {
        return Ok(MintOutcome::Denied(reason));
    }
    let minted = insert_ticket(&mut transaction, request, now).await?;
    transaction.commit().await?;
    Ok(MintOutcome::Minted(minted))
}

async fn insert_ticket(
    connection: &mut PgConnection,
    request: MintRequest,
    now: Instant,
) -> Result<MintedTicket, TicketError> {
    let ticket = random_hex(&OsRandom, TOKEN_BYTES)?;
    let ticket_id = uuid_v7(now.unix_millis(), &OsRandom)?;
    let expires_at = now
        .checked_add(TICKET_LIFETIME)
        .ok_or(TicketError::TimeRange)?;
    sqlx::query(
        "insert into tickets (id, secret_hash, user_id, book_id, version_id, grant_version, issued_at, expires_at)
         values ($1, $2, $3, $4, $5,
                 (select grant_version from users where id = $3), $6, $7)",
    )
    .bind(ticket_id)
    .bind(hash_token(&ticket))
    .bind(request.user_id)
    .bind(request.book_id)
    .bind(request.version_id)
    .bind(now.to_offset_date_time())
    .bind(expires_at.to_offset_date_time())
    .execute(connection)
    .await?;
    Ok(MintedTicket {
        ticket,
        ticket_id,
        expires_at: expires_at.unix_seconds(),
    })
}

struct StoredTicket {
    secret_hash: Vec<u8>,
    user_id: Uuid,
    book_id: Uuid,
    version_id: Uuid,
    expires_at: Instant,
}

async fn load_ticket(
    connection: &mut PgConnection,
    ticket_id: Uuid,
) -> Result<Option<StoredTicket>, sqlx::Error> {
    let Some(row) = sqlx::query(
        "select secret_hash, user_id, book_id, version_id, expires_at from tickets where id = $1",
    )
    .bind(ticket_id)
    .fetch_optional(connection)
    .await?
    else {
        return Ok(None);
    };
    Ok(Some(StoredTicket {
        secret_hash: row.try_get("secret_hash")?,
        user_id: row.try_get("user_id")?,
        book_id: row.try_get("book_id")?,
        version_id: row.try_get("version_id")?,
        expires_at: Instant::from_offset_date_time(row.try_get("expires_at")?),
    }))
}

fn matches_request(stored: &StoredTicket, request: &VerifyRequest<'_>) -> bool {
    stored.secret_hash == hash_token(request.ticket)
        && stored.book_id == request.book_id
        && stored.version_id == request.version_id
}

/// Verifies a ticket; `redeem` consumes read-once atomically and idempotently per ticket.
///
/// The access decision is re-run on every verify, which covers a moved grant version, a
/// suspended user and expired grants at once.
///
/// # Errors
/// [`TicketError`] on database failure.
pub async fn verify(
    pool: &PgPool,
    request: VerifyRequest<'_>,
    now: Instant,
) -> Result<VerifyOutcome, TicketError> {
    let mut transaction = pool.begin().await?;
    let outcome = check(&mut transaction, &request, now).await?;
    transaction.commit().await?;
    Ok(outcome)
}

/// Unknown, mismatching and expired tickets, before any access decision.
async fn screen(
    connection: &mut PgConnection,
    request: &VerifyRequest<'_>,
    now: Instant,
) -> Result<Result<StoredTicket, TicketDenial>, sqlx::Error> {
    let Some(stored) = load_ticket(connection, request.ticket_id).await? else {
        return Ok(Err(TicketDenial::Invalid));
    };
    if !matches_request(&stored, request) {
        return Ok(Err(TicketDenial::Invalid));
    }
    if now >= stored.expires_at {
        return Ok(Err(TicketDenial::Expired));
    }
    Ok(Ok(stored))
}

async fn check(
    connection: &mut PgConnection,
    request: &VerifyRequest<'_>,
    now: Instant,
) -> Result<VerifyOutcome, sqlx::Error> {
    let stored = match screen(connection, request, now).await? {
        Ok(stored) => stored,
        Err(denial) => return Ok(VerifyOutcome::Denied(denial)),
    };
    let query = AccessQuery {
        user_id: stored.user_id,
        book_id: stored.book_id,
        ticket: Some(request.ticket_id),
        now,
    };
    let access = access(connection, &query).await?;
    let redemption = Redemption {
        request,
        query: &query,
        access,
    };
    match access {
        Access::Denied(DenyReason::ReadOnceConsumed) => {
            Ok(VerifyOutcome::Denied(TicketDenial::ReadOnceConsumed))
        }
        Access::Denied(_) => Ok(VerifyOutcome::Denied(TicketDenial::Invalid)),
        Access::Normal | Access::ReadOnce => finish(connection, &redemption).await,
    }
}

struct Redemption<'a> {
    request: &'a VerifyRequest<'a>,
    query: &'a AccessQuery,
    access: Access,
}

async fn finish(
    connection: &mut PgConnection,
    redemption: &Redemption<'_>,
) -> Result<VerifyOutcome, sqlx::Error> {
    let (request, query) = (redemption.request, redemption.query);
    if request.redeem && !redeem(connection, redemption).await? {
        return Ok(VerifyOutcome::Denied(TicketDenial::ReadOnceConsumed));
    }
    Ok(VerifyOutcome::Valid {
        user_id: query.user_id,
    })
}

/// Claims read-once when it applies and marks the ticket redeemed; false when another ticket
/// already holds the use.
async fn redeem(
    connection: &mut PgConnection,
    redemption: &Redemption<'_>,
) -> Result<bool, sqlx::Error> {
    if redemption.access == Access::ReadOnce && !claim_read_once(connection, redemption).await? {
        return Ok(false);
    }
    sqlx::query("update tickets set redeemed_at = coalesce(redeemed_at, $2) where id = $1")
        .bind(redemption.request.ticket_id)
        .bind(redemption.query.now.to_offset_date_time())
        .execute(connection)
        .await?;
    Ok(true)
}

/// Inserts the use, or finds it already held; true when this ticket holds it.
async fn claim_read_once(
    connection: &mut PgConnection,
    redemption: &Redemption<'_>,
) -> Result<bool, sqlx::Error> {
    let (request, query) = (redemption.request, redemption.query);
    sqlx::query(
        "insert into read_once_uses (user_id, book_id, ticket_id, consumed_at)
         values ($1, $2, $3, $4) on conflict (user_id, book_id) do nothing",
    )
    .bind(query.user_id)
    .bind(query.book_id)
    .bind(request.ticket_id)
    .bind(query.now.to_offset_date_time())
    .execute(&mut *connection)
    .await?;
    let holder = read_once_holder(connection, query).await?;
    Ok(holder == ReadOnceStatus::ConsumedBy(TicketId::from_uuid(request.ticket_id)))
}
