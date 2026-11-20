//! Notify's only HTTP surface: internal routes behind service tokens (REQ-NTF-011: no public
//! route; the gateway does not route `/api/notify`).

use axum::extract::{Path, State};
use axum::routing::get;
use axum::{Json, Router};
use contracts_http::CommonErrorCode;
use platform_internal_http::{HasVerifier, Peer, PeerRejection};
use platform_service_token::Verifier;
use sqlx::PgPool;
use uuid::Uuid;

use crate::status::{self, MessageStatus, Stats};

#[derive(Clone)]
struct Shared {
    pool: PgPool,
    verifier: Verifier,
}

impl HasVerifier for Shared {
    fn verifier(&self) -> &Verifier {
        &self.verifier
    }
}

/// The internal routes, ready to merge into the service's router.
pub fn routes(pool: PgPool, verifier: Verifier) -> Router {
    Router::new()
        .route("/internal/messages/{id}", get(message_route))
        .route("/internal/stats", get(stats_route))
        .with_state(Shared { pool, verifier })
}

/// Why a route answered with an error.
enum Failure {
    Rejected(PeerRejection),
    Missing,
    Internal,
}

impl From<PeerRejection> for Failure {
    fn from(rejection: PeerRejection) -> Self {
        Self::Rejected(rejection)
    }
}

impl From<sqlx::Error> for Failure {
    fn from(error: sqlx::Error) -> Self {
        tracing::error!(%error, "database failure");
        Self::Internal
    }
}

impl axum::response::IntoResponse for Failure {
    fn into_response(self) -> axum::response::Response {
        let (status, code) = match self {
            Self::Rejected(rejection) => return rejection.into_response(),
            Self::Missing => (axum::http::StatusCode::NOT_FOUND, CommonErrorCode::NotFound),
            Self::Internal => (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                CommonErrorCode::InternalError,
            ),
        };
        let envelope = contracts_http::ErrorEnvelope::new(code, "The request failed.", "internal");
        (status, Json(envelope)).into_response()
    }
}

async fn message_route(
    State(shared): State<Shared>,
    peer: Peer,
    Path(id): Path<String>,
) -> Result<Json<MessageStatus>, Failure> {
    peer.only(&["identity", "catalog"])?;
    let id = Uuid::parse_str(&id).map_err(|_| Failure::Missing)?;
    let found = status::message(&shared.pool, id).await?;
    found.map(Json).ok_or(Failure::Missing)
}

async fn stats_route(State(shared): State<Shared>, peer: Peer) -> Result<Json<Stats>, Failure> {
    peer.only(&["identity", "catalog"])?;
    Ok(Json(status::stats(&shared.pool).await?))
}
