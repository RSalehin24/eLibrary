//! Every error the gateway itself produces is the typed envelope (REQ-GWY-012, INV-GWY-012);
//! this is the one place that maps them to a response.

use axum::Json;
use axum::http::header::RETRY_AFTER;
use axum::http::{HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use contracts_http::{CommonErrorCode, ErrorBody, ErrorEnvelope};

type Code = CommonErrorCode;

const PEER: Code = Code::PeerUnavailable;
const BUSY: &str = "The service is busy or not reachable. Try again shortly.";

/// Why the gateway answered instead of the upstream.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GatewayError {
    NotFound,
    Unauthenticated,
    /// Identity denied the session; the reason from identity is passed on.
    Denied(String),
    CsrfInvalid,
    RateLimited {
        retry_after_seconds: u64,
    },
    BodyTooLarge,
    /// Identity could not be reached or gave a garbled answer: never allow.
    IdentityUnavailable,
    UpstreamFailed,
    UpstreamTimeout,
    Overloaded,
}

impl GatewayError {
    fn code(&self) -> Code {
        match self {
            Self::NotFound => Code::NotFound,
            Self::Unauthenticated => Code::Unauthenticated,
            Self::Denied(reason) if reason == "mfa_incomplete" => Code::MfaRequired,
            Self::Denied(_) => Code::Forbidden,
            Self::CsrfInvalid => Code::CsrfInvalid,
            Self::RateLimited { .. } => Code::RateLimited,
            Self::BodyTooLarge => Code::BodyTooLarge,
            Self::IdentityUnavailable | Self::UpstreamFailed | Self::Overloaded => PEER,
            Self::UpstreamTimeout => Code::Timeout,
        }
    }

    fn message(&self) -> &'static str {
        match self {
            Self::NotFound => "There is nothing at this address.",
            Self::Unauthenticated => "Sign in to continue.",
            Self::Denied(_) => "This account may not do that.",
            Self::CsrfInvalid => "The request did not come from this site.",
            Self::RateLimited { .. } => "Too many requests. Try again later.",
            Self::BodyTooLarge => "The request is too large.",
            Self::IdentityUnavailable | Self::UpstreamFailed | Self::Overloaded => BUSY,
            Self::UpstreamTimeout => "The service took too long to answer.",
        }
    }

    fn retry_after(&self) -> Option<u64> {
        match self {
            Self::RateLimited {
                retry_after_seconds,
            } => Some(*retry_after_seconds),
            Self::IdentityUnavailable | Self::Overloaded => Some(2),
            Self::NotFound
            | Self::Unauthenticated
            | Self::Denied(_)
            | Self::CsrfInvalid
            | Self::BodyTooLarge
            | Self::UpstreamFailed
            | Self::UpstreamTimeout => None,
        }
    }

    fn details(&self) -> Option<serde_json::Value> {
        match self {
            Self::Denied(reason) => Some(serde_json::json!({ "reason": reason })),
            Self::NotFound
            | Self::Unauthenticated
            | Self::CsrfInvalid
            | Self::RateLimited { .. }
            | Self::BodyTooLarge
            | Self::IdentityUnavailable
            | Self::UpstreamFailed
            | Self::UpstreamTimeout
            | Self::Overloaded => None,
        }
    }

    /// The envelope response carrying the request id.
    #[must_use]
    pub fn respond(&self, request_id: &str) -> Response {
        let code = self.code();
        let envelope = ErrorEnvelope {
            error: ErrorBody {
                code: code.as_str().to_owned(),
                message: self.message().to_owned(),
                request_id: request_id.to_owned(),
                details: self.details(),
            },
        };
        let status = StatusCode::from_u16(code.http_status()).unwrap_or(StatusCode::BAD_GATEWAY);
        let response = (status, Json(envelope)).into_response();
        match self.retry_after() {
            Some(seconds) => with_retry_after(seconds, response),
            None => response,
        }
    }
}

fn with_retry_after(seconds: u64, mut response: Response) -> Response {
    response
        .headers_mut()
        .insert(RETRY_AFTER, HeaderValue::from(seconds));
    response
}

#[cfg(test)]
mod tests {
    use super::GatewayError;
    use axum::http::StatusCode;

    #[test]
    fn statuses_follow_the_error_catalog() {
        let status = |error: GatewayError| error.respond("r").status();
        assert_eq!(status(GatewayError::NotFound), StatusCode::NOT_FOUND);
        assert_eq!(
            status(GatewayError::Unauthenticated),
            StatusCode::UNAUTHORIZED
        );
        assert_eq!(status(GatewayError::CsrfInvalid), StatusCode::FORBIDDEN);
        assert_eq!(
            status(GatewayError::IdentityUnavailable),
            StatusCode::SERVICE_UNAVAILABLE
        );
        assert_eq!(
            status(GatewayError::UpstreamTimeout),
            StatusCode::GATEWAY_TIMEOUT
        );
        assert_eq!(
            status(GatewayError::BodyTooLarge),
            StatusCode::PAYLOAD_TOO_LARGE
        );
    }

    #[test]
    fn unavailable_and_limited_carry_retry_after() {
        let limited = GatewayError::RateLimited {
            retry_after_seconds: 7,
        }
        .respond("r");
        assert_eq!(
            limited
                .headers()
                .get("retry-after")
                .and_then(|v| v.to_str().ok()),
            Some("7")
        );
        let busy = GatewayError::IdentityUnavailable.respond("r");
        assert!(busy.headers().get("retry-after").is_some());
    }
}
