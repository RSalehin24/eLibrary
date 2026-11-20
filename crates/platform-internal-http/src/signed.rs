use std::time::Duration;

use axum::body::Body;
use axum::http::header::{AUTHORIZATION, CONTENT_TYPE};
use axum::http::{Method, Request, StatusCode};
use platform_service_token::{IssueRequest, ServiceName, TokenIssuer};
use platform_time::Instant;
use serde::Serialize;

use crate::{Fault, UpstreamClient};

const TOKEN_LIFETIME: Duration = Duration::from_secs(30);
const ANSWER_LIMIT: usize = 1024 * 1024;

/// A service that calls others: its signing identity and the shared client.
pub struct Caller {
    issuer: TokenIssuer,
    client: UpstreamClient,
}

/// One call: where, to which service, when, how long to wait, and an optional JSON body.
#[derive(Clone)]
pub struct SignedCall<'a> {
    pub method: Method,
    pub url: &'a str,
    pub callee: &'a str,
    pub timeout: Duration,
    pub now: Instant,
    pub body: Option<Vec<u8>>,
}

impl SignedCall<'_> {
    /// A JSON body from a value; `None` when it cannot be serialized.
    #[must_use]
    pub fn json_body<B: Serialize>(value: &B) -> Option<Vec<u8>> {
        serde_json::to_vec(value).ok()
    }
}

/// The status and the (size-bounded) body of the answer.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reply {
    pub status: StatusCode,
    pub body: Vec<u8>,
}

impl Caller {
    #[must_use]
    pub fn new(issuer: TokenIssuer) -> Self {
        Self {
            issuer,
            client: UpstreamClient::default(),
        }
    }

    /// Sends a signed call.
    ///
    /// # Errors
    /// [`Fault`] when the callee cannot be named or signed for, or does not answer in time.
    pub async fn call(&self, call: SignedCall<'_>) -> Result<Reply, Fault> {
        let callee = ServiceName::parse(call.callee).map_err(|_| Fault::Unreachable)?;
        let token = self
            .issuer
            .issue(IssueRequest {
                callee: &callee,
                now: call.now,
                lifetime: TOKEN_LIFETIME,
            })
            .ok_or(Fault::Unreachable)?;
        let request = Request::builder()
            .method(call.method)
            .uri(call.url)
            .header(AUTHORIZATION, format!("Service {}", token.as_str()))
            .header(CONTENT_TYPE, "application/json")
            .body(call.body.map_or_else(Body::empty, Body::from))
            .map_err(|_| Fault::Unreachable)?;
        let response = self.client.send(request, call.timeout).await?;
        let status = response.status();
        let bytes = axum::body::to_bytes(response.into_body(), ANSWER_LIMIT)
            .await
            .map_err(|_| Fault::Unreachable)?;
        Ok(Reply {
            status,
            body: bytes.to_vec(),
        })
    }
}
