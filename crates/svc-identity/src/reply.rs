//! Responses: the session cookie on success and the one error envelope on failure.

use axum::Json;
use axum::http::header::{RETRY_AFTER, SET_COOKIE};
use axum::http::{HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use contracts_http::{ErrorBody, ErrorEnvelope};
use platform_random::{OsRandom, uuid_v7};
use platform_time::{Clock, SystemClock};
use serde::Serialize;

use crate::cookie;
use crate::session::SessionError;
use crate::sign_in::SignInError;
use crate::throttle::WINDOW;
use crate::totp_verify::TotpVerifyError;

/// A success response that may set or clear the session cookie.
pub(crate) struct Reply(Option<HeaderValue>);

impl Reply {
    pub(crate) fn with_session(token: &str) -> Self {
        Self(cookie::set(token))
    }

    pub(crate) fn cleared_session() -> Self {
        Self(Some(cookie::clear()))
    }

    pub(crate) fn json<T: Serialize>(self, body: &T) -> Response {
        self.finish(Json(body).into_response())
    }

    pub(crate) fn empty(self) -> Response {
        self.finish(StatusCode::NO_CONTENT.into_response())
    }

    fn finish(self, response: Response) -> Response {
        with_cookie(response, self.0)
    }
}

fn with_cookie(mut response: Response, cookie: Option<HeaderValue>) -> Response {
    if let Some(value) = cookie {
        response.headers_mut().append(SET_COOKIE, value);
    }
    response
}

fn with_retry_after(mut response: Response) -> Response {
    response
        .headers_mut()
        .insert(RETRY_AFTER, HeaderValue::from(WINDOW.as_secs()));
    response
}

/// Every way these routes fail; the single place that maps them to HTTP.
pub(crate) enum Failure {
    InvalidCredentials,
    InvalidCode,
    RateLimited,
    Unauthenticated,
    Internal,
}

impl From<sqlx::Error> for Failure {
    fn from(error: sqlx::Error) -> Self {
        tracing::error!(%error, "database failure");
        Self::Internal
    }
}

impl From<SessionError> for Failure {
    fn from(error: SessionError) -> Self {
        tracing::error!(%error, "session failure");
        Self::Internal
    }
}

impl From<TotpVerifyError> for Failure {
    fn from(error: TotpVerifyError) -> Self {
        tracing::error!(%error, "totp failure");
        Self::Internal
    }
}

impl From<SignInError> for Failure {
    fn from(error: SignInError) -> Self {
        tracing::error!(%error, "sign-in failure");
        Self::Internal
    }
}

impl Failure {
    fn parts(&self) -> (StatusCode, &'static str, &'static str) {
        match self {
            Self::InvalidCredentials => (
                StatusCode::UNAUTHORIZED,
                "invalid_credentials",
                "The email or password is not right.",
            ),
            Self::InvalidCode => (
                StatusCode::UNPROCESSABLE_ENTITY,
                "invalid_code",
                "The code is not right or was already used.",
            ),
            Self::RateLimited => (
                StatusCode::TOO_MANY_REQUESTS,
                "rate_limited",
                "Too many attempts. Try again later.",
            ),
            Self::Unauthenticated => (
                StatusCode::UNAUTHORIZED,
                "unauthenticated",
                "There is no valid session.",
            ),
            Self::Internal => (
                StatusCode::INTERNAL_SERVER_ERROR,
                "internal_error",
                "Something went wrong.",
            ),
        }
    }
}

impl IntoResponse for Failure {
    fn into_response(self) -> Response {
        let (status, code, message) = self.parts();
        let envelope = ErrorEnvelope {
            error: ErrorBody {
                code: code.to_owned(),
                message: message.to_owned(),
                request_id: request_id(),
                details: None,
            },
        };
        let response = (status, Json(envelope)).into_response();
        match self {
            Self::RateLimited => with_retry_after(response),
            Self::InvalidCredentials
            | Self::InvalidCode
            | Self::Unauthenticated
            | Self::Internal => response,
        }
    }
}

// why: the gateway does not pass a request id yet; a fresh one still lets support find the log line.
fn request_id() -> String {
    uuid_v7(SystemClock.now().unix_millis(), &OsRandom)
        .map_or_else(|_| "unknown".to_owned(), |id| id.to_string())
}
