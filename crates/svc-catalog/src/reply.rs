//! Responses: the one error envelope, the public cache header and the slug redirect.

use axum::Json;
use axum::http::header::{CACHE_CONTROL, LOCATION};
use axum::http::{HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use contracts_http::{CommonErrorCode, ErrorBody, ErrorEnvelope};
use serde::Serialize;

const PUBLIC_CACHE: &str = "public, max-age=60";

/// Every way the public reads fail; the single place that maps them to HTTP.
pub(crate) enum Failure {
    /// The named request parameter is not valid or not supported yet.
    Invalid(&'static str),
    NotFound,
    /// The slug is an old one; the book now has this slug.
    Moved(String),
    Internal,
}

impl From<sqlx::Error> for Failure {
    fn from(error: sqlx::Error) -> Self {
        tracing::error!(%error, "database failure");
        Self::Internal
    }
}

#[derive(Serialize)]
struct Redirect<'a> {
    redirect_to: &'a str,
}

impl IntoResponse for Failure {
    fn into_response(self) -> Response {
        match self {
            Self::Moved(slug) => moved(&slug),
            Self::Invalid(field) => envelope(
                CommonErrorCode::ValidationFailed,
                "The request has a field that is not valid.",
                Some(field),
            ),
            Self::NotFound => envelope(CommonErrorCode::NotFound, "There is no such book.", None),
            Self::Internal => envelope(
                CommonErrorCode::InternalError,
                "Something went wrong.",
                None,
            ),
        }
    }
}

fn envelope(code: CommonErrorCode, message: &str, field: Option<&str>) -> Response {
    let body = ErrorEnvelope {
        error: ErrorBody {
            code: code.as_str().to_owned(),
            message: message.to_owned(),
            // why: the gateway does not pass a request id yet.
            request_id: String::new(),
            details: field.map(|name| serde_json::json!({ "fields": [name] })),
        },
    };
    let status =
        StatusCode::from_u16(code.http_status()).unwrap_or(StatusCode::INTERNAL_SERVER_ERROR);
    (status, Json(body)).into_response()
}

fn moved(slug: &str) -> Response {
    let target = format!("/api/catalog/books/{slug}");
    let mut response = (
        StatusCode::MOVED_PERMANENTLY,
        Json(Redirect { redirect_to: slug }),
    )
        .into_response();
    if let Ok(value) = HeaderValue::from_str(&target) {
        response.headers_mut().insert(LOCATION, value);
    }
    response
}

/// A public metadata body: JSON with the shared cache header.
pub(crate) fn public_json<T: Serialize>(body: &T) -> Response {
    let mut response = Json(body).into_response();
    response
        .headers_mut()
        .insert(CACHE_CONTROL, HeaderValue::from_static(PUBLIC_CACHE));
    response
}
