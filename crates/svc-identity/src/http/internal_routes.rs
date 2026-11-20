//! The internal routes (`/internal/...`): only services with a valid service token may call
//! them, and each route names the callers it serves (contract, "Internal routes").

use std::sync::Arc;

use axum::extract::{FromRequestParts, Path, RawQuery, State};
use axum::http::HeaderMap;
use axum::http::header::AUTHORIZATION;
use axum::http::request::Parts;
use axum::routing::{get, post};
use axum::{Json, Router};
use contracts_http::CommonErrorCode;
use platform_service_token::bearer_token;
use platform_time::{Clock, SystemClock};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use super::Shared;
use crate::internal_authz::{
    self, Authorization, AuthorizeRequest, AuthzDenial, CheckRequest, CheckResult, reason_name,
};
use crate::internal_reads::{self, EmailRequest, EventPage, MailContext, UserInfo};
use crate::query;
use crate::reply::Failure;
use crate::tickets::{self, MintOutcome, MintRequest, MintedTicket, VerifyOutcome, VerifyRequest};

pub(super) fn routes() -> Router<Arc<Shared>> {
    Router::new()
        .route("/internal/authorize", post(authorize_route))
        .route("/internal/check", post(check_route))
        .route("/internal/tickets", post(mint_route))
        .route("/internal/tickets/verify", post(verify_route))
        .route("/internal/users/{id}", get(user_route))
        .route(
            "/internal/users/{id}/grant-version",
            get(grant_version_route),
        )
        .route(
            "/internal/email-requests/{request_id}",
            get(email_request_route),
        )
        .route("/internal/events", get(events_route))
}

/// The service that presented a valid token.
struct Caller(String);

impl Caller {
    fn from_headers(headers: &HeaderMap, shared: &Shared) -> Result<Self, Failure> {
        let token = headers
            .get(AUTHORIZATION)
            .and_then(|value| value.to_str().ok())
            .and_then(bearer_token)
            .ok_or(Failure::ServiceToken)?;
        let caller = shared
            .verifier
            .verify(token, SystemClock.now())
            .map_err(|_| Failure::ServiceToken)?;
        Ok(Self(caller.as_str().to_owned()))
    }

    /// Refuses a caller the route does not serve (403).
    fn only(&self, allowed: &[&str]) -> Result<(), Failure> {
        allowed
            .contains(&self.0.as_str())
            .then_some(())
            .ok_or(Failure::Refused(CommonErrorCode::Forbidden))
    }
}

impl FromRequestParts<Arc<Shared>> for Caller {
    type Rejection = Failure;

    fn from_request_parts(
        parts: &mut Parts,
        shared: &Arc<Shared>,
    ) -> impl Future<Output = Result<Self, Failure>> + Send {
        std::future::ready(Self::from_headers(&parts.headers, shared))
    }
}

fn not_found() -> Failure {
    Failure::Refused(CommonErrorCode::NotFound)
}

fn user_key(text: &str) -> Result<Uuid, Failure> {
    text.parse::<contracts_ids::UserId>()
        .map(|id| id.as_uuid())
        .map_err(|_| not_found())
}

#[derive(Serialize)]
struct Allowed {
    user_id: String,
    scopes: Vec<&'static str>,
    grant_version: i64,
}

async fn authorize_route(
    State(shared): State<Arc<Shared>>,
    caller: Caller,
    Json(body): Json<AuthorizeRequest>,
) -> Result<Json<Allowed>, Failure> {
    caller.only(&["gateway"])?;
    let outcome = internal_authz::authorize(&shared.pool, &body, SystemClock.now()).await?;
    match outcome {
        Authorization::Allow {
            user_id,
            scopes,
            grant_version,
        } => Ok(Json(Allowed {
            user_id: contracts_ids::UserId::from_uuid(user_id).to_string(),
            scopes,
            grant_version,
        })),
        Authorization::NoSession => Err(Failure::Unauthenticated),
        Authorization::Denied { reason } => Err(Failure::Denied(denial_name(reason))),
    }
}

fn denial_name(reason: AuthzDenial) -> &'static str {
    match reason {
        AuthzDenial::AccountInactive => "account_inactive",
        AuthzDenial::TotpIncomplete => "mfa_incomplete",
        AuthzDenial::CsrfInvalid => "csrf_invalid",
    }
}

async fn check_route(
    State(shared): State<Arc<Shared>>,
    caller: Caller,
    Json(body): Json<CheckRequest>,
) -> Result<Json<CheckResult>, Failure> {
    caller.only(&["catalog", "reader", "ingestion", "notify"])?;
    Ok(Json(
        internal_authz::check(&shared.pool, &body, SystemClock.now()).await?,
    ))
}

async fn mint_route(
    State(shared): State<Arc<Shared>>,
    caller: Caller,
    Json(request): Json<MintRequest>,
) -> Result<Json<MintedTicket>, Failure> {
    caller.only(&["reader"])?;
    match tickets::mint(&shared.pool, request, SystemClock.now()).await? {
        MintOutcome::Minted(ticket) => Ok(Json(ticket)),
        MintOutcome::Denied(reason) => Err(Failure::Denied(reason_name(reason))),
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct VerifyBody {
    ticket_id: Uuid,
    ticket: String,
    book_id: Uuid,
    version_id: Uuid,
    #[serde(default)]
    redeem: bool,
}

#[derive(Serialize)]
struct Verified {
    user_id: String,
}

async fn verify_route(
    State(shared): State<Arc<Shared>>,
    caller: Caller,
    Json(body): Json<VerifyBody>,
) -> Result<Json<Verified>, Failure> {
    caller.only(&["reader"])?;
    let request = VerifyRequest {
        ticket_id: body.ticket_id,
        ticket: &body.ticket,
        book_id: body.book_id,
        version_id: body.version_id,
        redeem: body.redeem,
    };
    match tickets::verify(&shared.pool, request, SystemClock.now()).await? {
        VerifyOutcome::Valid { user_id } => Ok(Json(Verified {
            user_id: contracts_ids::UserId::from_uuid(user_id).to_string(),
        })),
        VerifyOutcome::Denied(denial) => Err(Failure::Ticket(denial.code())),
    }
}

async fn user_route(
    State(shared): State<Arc<Shared>>,
    caller: Caller,
    Path(id): Path<String>,
) -> Result<Json<UserInfo>, Failure> {
    caller.only(&["notify", "catalog"])?;
    let info = internal_reads::user_info(&shared.pool, user_key(&id)?).await?;
    info.map(Json).ok_or_else(not_found)
}

#[derive(Serialize)]
struct GrantVersion {
    grant_version: i64,
}

async fn grant_version_route(
    State(shared): State<Arc<Shared>>,
    caller: Caller,
    Path(id): Path<String>,
) -> Result<Json<GrantVersion>, Failure> {
    caller.only(&["reader", "catalog"])?;
    let version = internal_reads::grant_version(&shared.pool, user_key(&id)?).await?;
    version
        .map(|grant_version| Json(GrantVersion { grant_version }))
        .ok_or_else(not_found)
}

async fn email_request_route(
    State(shared): State<Arc<Shared>>,
    caller: Caller,
    Path(request_id): Path<String>,
) -> Result<Json<EmailRequest>, Failure> {
    caller.only(&["notify"])?;
    let context = MailContext {
        pool: &shared.pool,
        key: &shared.key,
        origin: &shared.origin,
    };
    let mail = internal_reads::email_request(context, &request_id, SystemClock.now()).await?;
    mail.map(Json).ok_or_else(not_found)
}

async fn events_route(
    State(shared): State<Arc<Shared>>,
    caller: Caller,
    RawQuery(raw): RawQuery,
) -> Result<Json<EventPage>, Failure> {
    caller.only(&["reader", "catalog", "notify"])?;
    let params = query::parse(raw.as_deref());
    let after = whole_number(&params, "after", 0)?;
    let limit = whole_number(&params, "limit", 100)?;
    let page = internal_reads::events_after(&shared.pool, after, limit).await?;
    Ok(Json(page))
}

fn whole_number(
    params: &std::collections::HashMap<String, String>,
    name: &'static str,
    default: i64,
) -> Result<i64, Failure> {
    match params.get(name) {
        None => Ok(default),
        Some(text) => text.parse::<i64>().map_err(|_| Failure::Invalid(name)),
    }
}
