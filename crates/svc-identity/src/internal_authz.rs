//! The internal gateway and service operations: `authorize` (session to capabilities) and
//! `check` (the pure `decide` over loaded facts). Routes and service-token wiring live elsewhere.

use contracts_http::Scope;
use contracts_ids::{BookId, TicketId};
use domain_access::{
    AccountStatus, BookFacts, Decision, DecisionInput, DenyReason, Grant, ReadOnceStatus, Role,
    Subject, UserFacts, decide,
};
use platform_time::Instant;
use serde::{Deserialize, Serialize};
use sqlx::{PgPool, Row};
use thiserror::Error;
use uuid::Uuid;

use crate::capabilities;
use crate::session::{self, SessionState};

#[derive(Debug, Error)]
pub enum AuthzError {
    #[error("database: {0}")]
    Database(#[from] sqlx::Error),
    #[error("session: {0}")]
    Session(#[from] session::SessionError),
    #[error("stored account data is not recognised")]
    UnknownStored,
}

/// What the gateway forwards for one request.
#[derive(Debug, Clone, Deserialize)]
pub struct AuthorizeRequest {
    pub method: String,
    pub path: String,
    /// The raw session cookie value, when the request carried one (`cookie` on the wire).
    #[serde(alias = "cookie")]
    pub cookie_token: Option<String>,
    pub origin: Option<String>,
    pub csrf_token: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AuthzDenial {
    AccountInactive,
    TotpIncomplete,
    CsrfInvalid,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Authorization {
    Allow {
        user_id: Uuid,
        scopes: Vec<&'static str>,
        grant_version: i64,
    },
    /// 401.
    NoSession,
    /// 403 with a reason.
    Denied { reason: AuthzDenial },
}

fn is_mutating(method: &str) -> bool {
    !["GET", "HEAD", "OPTIONS"]
        .iter()
        .any(|safe| method.eq_ignore_ascii_case(safe))
}

fn csrf_ok(request: &AuthorizeRequest, token: &str) -> bool {
    !is_mutating(&request.method)
        || request
            .csrf_token
            .as_deref()
            .is_some_and(|given| given == session::csrf_token_for(token))
}

/// Resolves a cookie to the caller's capabilities, or says why not.
///
/// # Errors
/// Database failures.
pub async fn authorize(
    pool: &PgPool,
    request: &AuthorizeRequest,
    now: Instant,
) -> Result<Authorization, AuthzError> {
    let Some(token) = request.cookie_token.as_deref() else {
        return Ok(Authorization::NoSession);
    };
    let Some(live) = session::lookup(pool, token, now).await? else {
        return Ok(Authorization::NoSession);
    };
    if live.state != SessionState::Authenticated {
        return Ok(denied(AuthzDenial::TotpIncomplete));
    }
    let Some(caps) = capabilities::resolve(pool, live.user_id, now).await? else {
        return Ok(denied(AuthzDenial::AccountInactive));
    };
    if !csrf_ok(request, token) {
        return Ok(denied(AuthzDenial::CsrfInvalid));
    }
    let grant_version = grant_version(pool, live.user_id).await?;
    Ok(Authorization::Allow {
        user_id: live.user_id,
        scopes: caps.scope_names().to_vec(),
        grant_version,
    })
}

fn denied(reason: AuthzDenial) -> Authorization {
    Authorization::Denied { reason }
}

async fn grant_version(pool: &PgPool, user_id: Uuid) -> Result<i64, sqlx::Error> {
    sqlx::query_scalar("select grant_version from users where id = $1")
        .bind(user_id)
        .fetch_one(pool)
        .await
}

/// The catalog's facts about the book, as the caller supplies them.
#[derive(Debug, Clone, Copy, Deserialize)]
pub struct BookState {
    pub published: bool,
    pub deleted: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CheckRequest {
    pub user_id: Uuid,
    pub scope: String,
    pub book_id: Option<Uuid>,
    pub book_state: Option<BookState>,
}

/// The wire form: `{decision: "allow"}` or `{decision: "deny", reason}`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "decision", rename_all = "snake_case")]
pub enum CheckResult {
    Allow,
    Deny { reason: &'static str },
}

/// The stable wire name of a deny reason (error catalog, "Deny reasons").
#[must_use]
pub fn reason_name(reason: DenyReason) -> &'static str {
    match reason {
        DenyReason::GrantExpired => "grant_expired",
        DenyReason::AccountInactive => "account_inactive",
        DenyReason::MfaIncomplete => "mfa_incomplete",
        DenyReason::BookNotPublished => "book_not_published",
        DenyReason::BookDeleted => "book_deleted",
        DenyReason::ReadOnceConsumed => "read_once_consumed",
        // why: NoScope and any future reason map to the deny-by-default name.
        DenyReason::NoScope | _ => "no_scope",
    }
}

fn result_of(decision: Decision) -> CheckResult {
    match decision {
        Decision::Allow => CheckResult::Allow,
        Decision::Deny(reason) => CheckResult::Deny {
            reason: reason_name(reason),
        },
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

fn role_of(name: &str) -> Option<Role> {
    match name {
        "reader" => Some(Role::Reader),
        "operator" => Some(Role::Operator),
        "admin" => Some(Role::Admin),
        _ => None,
    }
}

async fn load_subject(pool: &PgPool, user_id: Uuid) -> Result<Option<UserFacts>, AuthzError> {
    let row = sqlx::query("select status, role from users where id = $1")
        .bind(user_id)
        .fetch_optional(pool)
        .await?;
    let Some(row) = row else {
        return Ok(None);
    };
    let status: String = row.try_get("status")?;
    let role: String = row.try_get("role")?;
    Ok(Some(UserFacts {
        status: status_of(&status).ok_or(AuthzError::UnknownStored)?,
        role: role_of(&role).ok_or(AuthzError::UnknownStored)?,
        // why: the caller passes only users with an authenticated session.
        mfa_satisfied: true,
    }))
}

/// One grant row; `None` for a scope name this build does not know (it grants nothing).
fn grant_from(row: &sqlx::postgres::PgRow) -> Result<Option<Grant>, sqlx::Error> {
    let name: String = row.try_get("scope")?;
    let book: Option<Uuid> = row.try_get("book_id")?;
    let expires: Option<_> = row.try_get("expires_at")?;
    Ok(Scope::ALL
        .into_iter()
        .find(|s| s.as_str() == name)
        .map(|scope| Grant {
            scope,
            book: book.map(BookId::from_uuid),
            expires_at: expires.map(Instant::from_offset_date_time),
            revoked: false,
        }))
}

/// Active grants, expired ones included, so `decide` can tell `grant_expired` from `no_scope`.
async fn load_grants(pool: &PgPool, user_id: Uuid) -> Result<Vec<Grant>, AuthzError> {
    let rows =
        sqlx::query("select scope, book_id, expires_at from grants where user_id = $1 and active")
            .bind(user_id)
            .fetch_all(pool)
            .await?;
    let mut grants = Vec::new();
    for row in &rows {
        grants.extend(grant_from(row)?);
    }
    Ok(grants)
}

async fn read_once_status(
    pool: &PgPool,
    user_id: Uuid,
    book_id: Option<Uuid>,
) -> Result<ReadOnceStatus, sqlx::Error> {
    let ticket: Option<Uuid> = sqlx::query_scalar(
        "select ticket_id from read_once_uses where user_id = $1 and book_id = $2",
    )
    .bind(user_id)
    .bind(book_id)
    .fetch_optional(pool)
    .await?;
    Ok(ticket.map_or(ReadOnceStatus::Unused, |id| {
        ReadOnceStatus::ConsumedBy(TicketId::from_uuid(id))
    }))
}

fn book_facts(request: &CheckRequest) -> Option<BookFacts> {
    let (id, state) = (request.book_id?, request.book_state?);
    Some(BookFacts {
        id: BookId::from_uuid(id),
        published: state.published,
        deleted: state.deleted,
    })
}

async fn load_context(
    pool: &PgPool,
    request: &CheckRequest,
) -> Result<(Vec<Grant>, ReadOnceStatus), AuthzError> {
    let grants = load_grants(pool, request.user_id).await?;
    let read_once = read_once_status(pool, request.user_id, request.book_id).await?;
    Ok((grants, read_once))
}

/// The access decision for a user; total and deny by default.
///
/// # Errors
/// Database failures.
pub async fn check(
    pool: &PgPool,
    request: &CheckRequest,
    now: Instant,
) -> Result<CheckResult, AuthzError> {
    let Some(scope) = Scope::ALL.into_iter().find(|s| s.as_str() == request.scope) else {
        return Ok(CheckResult::Deny { reason: "no_scope" });
    };
    let Some(user) = load_subject(pool, request.user_id).await? else {
        return Ok(CheckResult::Deny {
            reason: "account_inactive",
        });
    };
    let (grants, read_once) = load_context(pool, request).await?;
    let input = DecisionInput {
        subject: Subject::User(user),
        scope,
        book: book_facts(request),
        grants: &grants,
        now,
        read_once,
        ticket: None,
    };
    Ok(result_of(decide(&input)))
}
