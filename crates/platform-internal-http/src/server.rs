//! The receiving side: an extractor that proves the caller is one of our services (a valid
//! service token addressed to this service) and lets a route name the callers it serves.

use axum::Json;
use axum::extract::FromRequestParts;
use axum::http::StatusCode;
use axum::http::header::AUTHORIZATION;
use axum::http::request::Parts;
use axum::response::{IntoResponse, Response};
use contracts_http::{CommonErrorCode, ErrorEnvelope};
use platform_service_token::{Verifier, bearer_token};
use platform_time::{Clock, SystemClock};

/// State that holds this service's token verifier.
pub trait HasVerifier {
    fn verifier(&self) -> &Verifier;
}

/// A service that presented a valid token.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Peer(String);

/// Why a request was refused before reaching the route.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PeerRejection {
    /// No token, or one that does not verify (401 `service_token_invalid`).
    Token,
    /// A valid caller the route does not serve (403 `forbidden`).
    NotAllowed,
}

impl Peer {
    /// The caller's service name.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.0
    }

    /// Refuses a caller the route does not serve.
    ///
    /// # Errors
    /// [`PeerRejection::NotAllowed`] when the caller is not in `allowed`.
    pub fn only(&self, allowed: &[&str]) -> Result<(), PeerRejection> {
        allowed
            .contains(&self.0.as_str())
            .then_some(())
            .ok_or(PeerRejection::NotAllowed)
    }
}

fn identify(parts: &Parts, verifier: &Verifier) -> Result<Peer, PeerRejection> {
    let token = parts
        .headers
        .get(AUTHORIZATION)
        .and_then(|value| value.to_str().ok())
        .and_then(bearer_token)
        .ok_or(PeerRejection::Token)?;
    let caller = verifier
        .verify(token, SystemClock.now())
        .map_err(|_| PeerRejection::Token)?;
    Ok(Peer(caller.as_str().to_owned()))
}

impl<S: HasVerifier + Send + Sync> FromRequestParts<S> for Peer {
    type Rejection = PeerRejection;

    fn from_request_parts(
        parts: &mut Parts,
        state: &S,
    ) -> impl Future<Output = Result<Self, PeerRejection>> + Send {
        std::future::ready(identify(parts, state.verifier()))
    }
}

impl IntoResponse for PeerRejection {
    fn into_response(self) -> Response {
        let (status, code, message) = match self {
            Self::Token => (
                StatusCode::UNAUTHORIZED,
                CommonErrorCode::ServiceTokenInvalid,
                "The service token is missing or not valid.",
            ),
            Self::NotAllowed => (
                StatusCode::FORBIDDEN,
                CommonErrorCode::Forbidden,
                "This service may not call this route.",
            ),
        };
        let envelope = ErrorEnvelope::new(code, message, "internal");
        (status, Json(envelope)).into_response()
    }
}
