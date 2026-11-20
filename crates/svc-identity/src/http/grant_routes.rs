//! The grant routes (`manage_users`): list, create, edit, revoke and batch.

use std::sync::Arc;

use axum::extract::{FromRequestParts, Path, RawQuery, State};
use axum::http::request::Parts;
use axum::http::{HeaderMap, StatusCode};
use axum::routing::{get, post};
use axum::{Json, Router};
use contracts_http::CommonErrorCode;
use platform_time::{Clock, SystemClock};
use serde::{Deserialize, Deserializer, Serialize};
use uuid::Uuid;

use super::{Shared, administrator, if_match};
use crate::grants::{
    self, Change, Edit, Expiry, GrantError, GrantRow, Listing, Refusal, Spec, Target, check_reason,
};
use crate::query;
use crate::reply::{Failure, Named};

pub(super) fn routes() -> Router<Arc<Shared>> {
    Router::new()
        .route("/api/identity/grants", get(list_route).post(create_route))
        .route("/api/identity/grants/batch", post(batch_route))
        .route(
            "/api/identity/grants/{id}",
            axum::routing::patch(edit_route).delete(revoke_route),
        )
}

impl From<GrantError> for Failure {
    fn from(error: GrantError) -> Self {
        match error {
            GrantError::Failed(inner) => inner.into(),
            GrantError::Refused(Refusal::Invalid(field)) => Self::Invalid(field),
            GrantError::Refused(Refusal::Duplicate) => Self::Named(Named::DuplicateGrant),
            GrantError::Refused(Refusal::Code(code)) => Self::Refused(code),
        }
    }
}

/// An administrator and the grant a `/grants/{id}` route is about, plus the `If-Match` revision.
struct AdminOnGrant {
    actor: Uuid,
    grant: Uuid,
    revision: Option<i64>,
}

impl FromRequestParts<Arc<Shared>> for AdminOnGrant {
    type Rejection = Failure;

    async fn from_request_parts(parts: &mut Parts, shared: &Arc<Shared>) -> Result<Self, Failure> {
        let actor = administrator(shared, &parts.headers).await?;
        let missing = || Failure::Refused(CommonErrorCode::NotFound);
        let Path(id) = Path::<String>::from_request_parts(parts, shared)
            .await
            .map_err(|_| missing())?;
        Ok(Self {
            actor,
            grant: Uuid::parse_str(&id).map_err(|_| missing())?,
            revision: if_match(&parts.headers),
        })
    }
}

/// The change by `parties` = (actor, user) with the given reason.
fn change<'a>(shared: &'a Shared, parties: (Uuid, Uuid), reason: &'a str) -> Change<'a> {
    Change {
        pool: &shared.pool,
        now: SystemClock.now(),
        actor: parties.0,
        user: parties.1,
        reason,
    }
}

fn user_id(text: &str, field: &'static str) -> Result<Uuid, Failure> {
    text.parse::<contracts_ids::UserId>()
        .map(|id| id.as_uuid())
        .map_err(|_| Failure::Invalid(field))
}

#[derive(Serialize)]
struct GrantPage {
    items: Vec<GrantRow>,
    next: Option<String>,
}

/// The first wrong list parameter's name, or the checked request.
fn listing(raw: Option<&str>) -> Result<Listing, Failure> {
    let params = query::parse(raw);
    let limit = match params.get("limit") {
        None => 100,
        Some(text) => text
            .parse::<i64>()
            .ok()
            .filter(|value| (1..=100).contains(value))
            .ok_or(Failure::Invalid("limit"))?,
    };
    let book = params
        .get("book_id")
        .map(|text| text.parse::<contracts_ids::BookId>().map(|id| id.as_uuid()))
        .transpose()
        .map_err(|_| Failure::Invalid("book_id"))?;
    let after = params
        .get("after")
        .map(|text| Uuid::parse_str(text))
        .transpose()
        .map_err(|_| Failure::Invalid("after"))?;
    Ok(Listing {
        user: params
            .get("user_id")
            .map(|text| user_id(text, "user_id"))
            .transpose()?,
        scope: params.get("scope").cloned(),
        book,
        after,
        limit,
    })
}

async fn list_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    RawQuery(raw): RawQuery,
) -> Result<Json<GrantPage>, Failure> {
    administrator(&shared, &headers).await?;
    let (items, next) = grants::list(&shared.pool, listing(raw.as_deref())?).await?;
    Ok(Json(GrantPage { items, next }))
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CreateBody {
    user_id: String,
    scope: String,
    book_id: Option<String>,
    expires_at: Option<i64>,
    reason: String,
}

async fn create_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Json(body): Json<CreateBody>,
) -> Result<(StatusCode, Json<GrantRow>), Failure> {
    let actor = administrator(&shared, &headers).await?;
    let user = user_id(&body.user_id, "user_id")?;
    let reason = check_reason(&body.reason).map_err(Failure::Invalid)?;
    let spec = Spec {
        scope: body.scope,
        book_id: body.book_id,
        expires_at: body.expires_at,
    };
    let row = grants::create(change(&shared, (actor, user), reason), &spec).await?;
    Ok((StatusCode::CREATED, Json(row)))
}

impl<'de> Deserialize<'de> for ExpiryField {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let value = Option::<i64>::deserialize(deserializer)?;
        Ok(Self(value.map_or(Expiry::Clear, Expiry::Set)))
    }
}

/// A present `expires_at`: `null` clears it, a number sets it; an absent one is `Keep`.
#[derive(Default)]
struct ExpiryField(Expiry);

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct EditBody {
    #[serde(default)]
    expires_at: ExpiryField,
    active: Option<bool>,
}

async fn edit_route(
    State(shared): State<Arc<Shared>>,
    admin: AdminOnGrant,
    Json(body): Json<EditBody>,
) -> Result<Json<GrantRow>, Failure> {
    let revision = admin.revision.ok_or(Failure::Invalid("if_match"))?;
    if matches!(body.expires_at.0, Expiry::Keep) && body.active.is_none() {
        return Err(Failure::Invalid("body"));
    }
    let target = Target {
        grant: admin.grant,
        revision,
    };
    let edit = Edit {
        expires_at: body.expires_at.0,
        active: body.active,
    };
    let row = grants::edit(
        change(&shared, (admin.actor, Uuid::nil()), ""),
        target,
        edit,
    )
    .await?;
    Ok(Json(row))
}

async fn revoke_route(
    State(shared): State<Arc<Shared>>,
    admin: AdminOnGrant,
) -> Result<StatusCode, Failure> {
    grants::revoke(change(&shared, (admin.actor, Uuid::nil()), ""), admin.grant).await?;
    Ok(StatusCode::NO_CONTENT)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct SpecBody {
    scope: String,
    book_id: Option<String>,
    expires_at: Option<i64>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct BatchBody {
    user_id: String,
    #[serde(default)]
    grant: Vec<SpecBody>,
    #[serde(default)]
    revoke: Vec<String>,
    reason: String,
}

#[derive(Serialize)]
struct BatchReply {
    granted: Vec<GrantRow>,
}

async fn batch_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Json(body): Json<BatchBody>,
) -> Result<Json<BatchReply>, Failure> {
    let actor = administrator(&shared, &headers).await?;
    let user = user_id(&body.user_id, "user_id")?;
    let reason = check_reason(&body.reason).map_err(Failure::Invalid)?;
    let specs: Vec<Spec> = body
        .grant
        .into_iter()
        .map(|spec| Spec {
            scope: spec.scope,
            book_id: spec.book_id,
            expires_at: spec.expires_at,
        })
        .collect();
    let revoke = body
        .revoke
        .iter()
        .map(|text| Uuid::parse_str(text))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| Failure::Invalid("revoke"))?;
    let granted = grants::batch(change(&shared, (actor, user), reason), &specs, &revoke).await?;
    Ok(Json(BatchReply { granted }))
}
