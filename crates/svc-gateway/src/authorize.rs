//! The identity call that decides every protected request (REQ-GWY-002). Any failure to get a
//! clear answer is `Unavailable`; the gateway never allows on error (INV-GWY-002).

use std::time::Duration;

use axum::body::Body;
use axum::http::header::{AUTHORIZATION, CONTENT_TYPE};
use axum::http::{Method, Request, StatusCode};
use serde::{Deserialize, Serialize};

use crate::headers::Identity;
use crate::upstream::UpstreamClient;

const ANSWER_LIMIT: usize = 16 * 1024;
const AUTHORIZE_TIMEOUT: Duration = Duration::from_secs(2);

/// The whole result of the identity call.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Verdict {
    Allow(Identity),
    Unauthenticated,
    /// Denied, with identity's reason (`account_inactive`, `mfa_incomplete`, `csrf_invalid`).
    Denied(String),
    Unavailable,
}

/// What the gateway tells identity about the request.
#[derive(Debug, Clone, Serialize)]
pub struct Question<'a> {
    pub method: &'a str,
    pub path: &'a str,
    pub cookie: Option<&'a str>,
    pub origin: Option<&'a str>,
    pub csrf_token: Option<&'a str>,
}

/// Where identity is and the service token to present.
#[derive(Debug, Clone)]
pub struct IdentityLink {
    pub base: String,
    pub service_token: String,
}

#[derive(Deserialize)]
struct Allowed {
    user_id: String,
    scopes: Vec<String>,
    grant_version: i64,
}

#[derive(Deserialize)]
struct Failure {
    error: FailureBody,
}

#[derive(Deserialize)]
struct FailureBody {
    details: Option<Reason>,
}

#[derive(Deserialize)]
struct Reason {
    reason: Option<String>,
}

/// Asks identity whether the request may proceed.
pub async fn authorize(
    client: &UpstreamClient,
    link: &IdentityLink,
    question: &Question<'_>,
) -> Verdict {
    let Ok(body) = serde_json::to_vec(question) else {
        return Verdict::Unavailable;
    };
    let request = Request::builder()
        .method(Method::POST)
        .uri(format!("{}/internal/authorize", link.base))
        .header(CONTENT_TYPE, "application/json")
        .header(AUTHORIZATION, format!("Service {}", link.service_token))
        .body(Body::from(body));
    let Ok(request) = request else {
        return Verdict::Unavailable;
    };
    let Ok(response) = client.send(request, AUTHORIZE_TIMEOUT).await else {
        return Verdict::Unavailable;
    };
    let status = response.status();
    let Ok(bytes) = axum::body::to_bytes(response.into_body(), ANSWER_LIMIT).await else {
        return Verdict::Unavailable;
    };
    verdict_of(status, &bytes)
}

/// Total mapping from identity's answer to a verdict.
#[must_use]
pub fn verdict_of(status: StatusCode, body: &[u8]) -> Verdict {
    match status {
        StatusCode::OK => allowed(body),
        StatusCode::UNAUTHORIZED => Verdict::Unauthenticated,
        StatusCode::FORBIDDEN => Verdict::Denied(denial_reason(body)),
        _ => Verdict::Unavailable,
    }
}

fn allowed(body: &[u8]) -> Verdict {
    match serde_json::from_slice::<Allowed>(body) {
        Ok(ok) => Verdict::Allow(Identity {
            user_id: ok.user_id,
            scopes: ok.scopes,
            grant_version: ok.grant_version,
        }),
        Err(_) => Verdict::Unavailable,
    }
}

fn denial_reason(body: &[u8]) -> String {
    serde_json::from_slice::<Failure>(body)
        .ok()
        .and_then(|failure| failure.error.details)
        .and_then(|details| details.reason)
        .unwrap_or_else(|| "forbidden".to_owned())
}

#[cfg(test)]
mod tests {
    use super::{Verdict, verdict_of};
    use axum::http::StatusCode;

    #[test]
    fn allow_needs_a_well_formed_body() {
        let good = br#"{"user_id":"u","scopes":["read"],"grant_version":3}"#;
        assert!(matches!(
            verdict_of(StatusCode::OK, good),
            Verdict::Allow(_)
        ));
        assert_eq!(verdict_of(StatusCode::OK, b"garbage"), Verdict::Unavailable);
        assert_eq!(verdict_of(StatusCode::OK, b"{}"), Verdict::Unavailable);
    }

    #[test]
    fn denial_carries_the_reason_and_everything_else_is_unavailable() {
        let denied = br#"{"error":{"code":"forbidden","message":"m","request_id":"r","details":{"reason":"csrf_invalid"}}}"#;
        assert_eq!(
            verdict_of(StatusCode::FORBIDDEN, denied),
            Verdict::Denied("csrf_invalid".into())
        );
        assert_eq!(
            verdict_of(StatusCode::FORBIDDEN, b"?"),
            Verdict::Denied("forbidden".into())
        );
        assert_eq!(
            verdict_of(StatusCode::UNAUTHORIZED, b""),
            Verdict::Unauthenticated
        );
        let statuses = [
            StatusCode::INTERNAL_SERVER_ERROR,
            StatusCode::BAD_GATEWAY,
            StatusCode::NOT_FOUND,
            StatusCode::NO_CONTENT,
        ];
        let allowed = statuses
            .into_iter()
            .filter(|status| verdict_of(*status, b"{}") != Verdict::Unavailable)
            .count();
        assert_eq!(allowed, 0);
    }
}
