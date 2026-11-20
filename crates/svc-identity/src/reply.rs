//! Responses: the session cookie on success and the one error envelope on failure.

use axum::Json;
use axum::http::header::{RETRY_AFTER, SET_COOKIE};
use axum::http::{HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use contracts_http::{CommonErrorCode, ErrorBody, ErrorEnvelope};
use platform_random::{OsRandom, uuid_v7};
use platform_time::{Clock, SystemClock};
use serde::Serialize;

use crate::admin_change::ChangeError;
use crate::cookie;
use crate::links::LinkError;
use crate::session::SessionError;
use crate::sign_in::SignInError;
use crate::throttle::WINDOW;
use crate::totp_manage::{ManageError, Outcome};
use crate::totp_verify::TotpVerifyError;

/// A success response that may set or clear the session cookie.
pub(crate) struct Reply(Option<HeaderValue>);

impl Reply {
    pub(crate) fn with_session(token: &str) -> Self {
        Self(cookie::set(token))
    }

    pub(crate) fn none() -> Self {
        Self(None)
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

/// Refusals with codes of their own (error catalog).
#[derive(Debug, Clone, Copy)]
pub(crate) enum Named {
    DuplicateGrant,
    EmailTaken,
    LinkInvalid,
    InvalidImage,
}

impl Named {
    fn parts(self) -> Parts {
        match self {
            Self::DuplicateGrant => (
                StatusCode::CONFLICT,
                "duplicate_grant",
                "The user already has this grant.",
            ),
            Self::EmailTaken => (
                StatusCode::CONFLICT,
                "email_taken",
                "That email address already has an account.",
            ),
            Self::InvalidImage => (
                StatusCode::UNPROCESSABLE_ENTITY,
                "invalid_image",
                "The image type or size is not accepted.",
            ),
            Self::LinkInvalid => (
                StatusCode::GONE,
                "link_invalid",
                "The link is not valid any more. Ask for a new one.",
            ),
        }
    }
}

/// Every way these routes fail; the single place that maps them to HTTP.
pub(crate) enum Failure {
    InvalidCredentials,
    InvalidCode,
    WeakPassword,
    /// A refusal with its own stable code.
    Named(Named),
    /// The action is denied, with the deny reason in `details.reason`.
    Denied(&'static str),
    /// The caller's service token is missing or not valid.
    ServiceToken,
    /// A reading ticket was refused, with its wire code.
    Ticket(&'static str),
    RateLimited,
    Unauthenticated,
    /// The named request field (or `body`) failed validation.
    Invalid(&'static str),
    /// The action is not allowed (forbidden, invalid transition).
    Refused(CommonErrorCode),
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

impl From<ManageError> for Failure {
    fn from(error: ManageError) -> Self {
        tracing::error!(%error, "totp management failure");
        Self::Internal
    }
}

impl<T> Outcome<T> {
    /// The success value, or the failure the outcome stands for.
    pub(crate) fn settle(self) -> Result<T, Failure> {
        match self {
            Self::Done(value) => Ok(value),
            Self::BadPassword => Err(Failure::InvalidCredentials),
            Self::BadCode => Err(Failure::InvalidCode),
            Self::Throttled => Err(Failure::RateLimited),
            Self::Weak => Err(Failure::WeakPassword),
            Self::Refused(code) => Err(Failure::Refused(code)),
        }
    }
}

impl From<crate::internal_authz::AuthzError> for Failure {
    fn from(error: crate::internal_authz::AuthzError) -> Self {
        tracing::error!(%error, "authorization failure");
        Self::Internal
    }
}

impl From<crate::tickets::TicketError> for Failure {
    fn from(error: crate::tickets::TicketError) -> Self {
        tracing::error!(%error, "ticket failure");
        Self::Internal
    }
}

impl From<crate::internal_reads::ReadError> for Failure {
    fn from(error: crate::internal_reads::ReadError) -> Self {
        tracing::error!(%error, "internal read failure");
        Self::Internal
    }
}

impl From<LinkError> for Failure {
    fn from(error: LinkError) -> Self {
        tracing::error!(%error, "link failure");
        Self::Internal
    }
}

impl From<ChangeError> for Failure {
    fn from(error: ChangeError) -> Self {
        tracing::error!(%error, "account change failure");
        Self::Internal
    }
}

impl From<SignInError> for Failure {
    fn from(error: SignInError) -> Self {
        tracing::error!(%error, "sign-in failure");
        Self::Internal
    }
}

/// Status, stable code and a safe message.
type Parts = (StatusCode, &'static str, &'static str);

impl Failure {
    fn parts(&self) -> Parts {
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
            Self::Named(_) | Self::WeakPassword | Self::Invalid(_) => self.input_parts(),
            Self::Refused(_)
            | Self::Denied(_)
            | Self::ServiceToken
            | Self::Ticket(_)
            | Self::Internal => self.fault_parts(),
        }
    }

    fn input_parts(&self) -> Parts {
        match self {
            Self::Named(named) => named.parts(),
            Self::WeakPassword => (
                StatusCode::UNPROCESSABLE_ENTITY,
                "weak_password",
                "The new password does not meet the password rules.",
            ),
            Self::Invalid(_)
            | Self::InvalidCredentials
            | Self::InvalidCode
            | Self::RateLimited
            | Self::Unauthenticated
            | Self::Refused(_)
            | Self::Denied(_)
            | Self::ServiceToken
            | Self::Ticket(_)
            | Self::Internal => (
                StatusCode::UNPROCESSABLE_ENTITY,
                "validation_failed",
                "The request has a field that is not valid.",
            ),
        }
    }

    fn fault_parts(&self) -> Parts {
        match self {
            Self::Refused(code) => (
                StatusCode::from_u16(code.http_status()).unwrap_or(StatusCode::FORBIDDEN),
                code.as_str(),
                "The action is not allowed.",
            ),
            Self::Denied(_) => (
                StatusCode::FORBIDDEN,
                "forbidden",
                "The action is not allowed.",
            ),
            Self::Ticket(code) => (ticket_status(code), code, "The reading ticket was refused."),
            Self::ServiceToken => (
                StatusCode::UNAUTHORIZED,
                "service_token_invalid",
                "The service token is missing or not valid.",
            ),
            Self::InvalidCredentials
            | Self::InvalidCode
            | Self::WeakPassword
            | Self::Named(_)
            | Self::RateLimited
            | Self::Unauthenticated
            | Self::Invalid(_)
            | Self::Internal => (
                StatusCode::INTERNAL_SERVER_ERROR,
                "internal_error",
                "Something went wrong.",
            ),
        }
    }

    fn details(&self) -> Option<serde_json::Value> {
        match self {
            Self::Invalid(field) => Some(serde_json::json!({ "fields": [field] })),
            Self::Denied(reason) => Some(serde_json::json!({ "reason": reason })),
            Self::InvalidCredentials
            | Self::InvalidCode
            | Self::WeakPassword
            | Self::Named(_)
            | Self::RateLimited
            | Self::Unauthenticated
            | Self::Refused(_)
            | Self::ServiceToken
            | Self::Ticket(_)
            | Self::Internal => None,
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
                details: self.details(),
            },
        };
        let response = (status, Json(envelope)).into_response();
        match self {
            Self::RateLimited => with_retry_after(response),
            Self::InvalidCredentials
            | Self::InvalidCode
            | Self::WeakPassword
            | Self::Named(_)
            | Self::Unauthenticated
            | Self::Invalid(_)
            | Self::Refused(_)
            | Self::Denied(_)
            | Self::ServiceToken
            | Self::Ticket(_)
            | Self::Internal => response,
        }
    }
}

// why: the gateway does not pass a request id yet; a fresh one still lets support find the log line.
fn request_id() -> String {
    uuid_v7(SystemClock.now().unix_millis(), &OsRandom)
        .map_or_else(|_| "unknown".to_owned(), |id| id.to_string())
}

/// `ticket_expired` is 410; the other ticket refusals are 403 (error catalog).
fn ticket_status(code: &str) -> StatusCode {
    if code == "ticket_expired" {
        StatusCode::GONE
    } else {
        StatusCode::FORBIDDEN
    }
}
