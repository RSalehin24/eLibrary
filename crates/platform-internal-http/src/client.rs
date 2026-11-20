//! Calls to the other services over internal HTTP, with a timeout and no retries. The body is
//! passed through as a stream in both directions (REQ-GWY-010).

use std::time::Duration;

use axum::body::Body;
use axum::http::{Request, Response};
use hyper_util::client::legacy::Client;
use hyper_util::client::legacy::connect::HttpConnector;
use hyper_util::rt::TokioExecutor;

/// Why a call to a service did not produce a response.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Fault {
    Timeout,
    Unreachable,
}

/// The shared HTTP client for all upstream calls.
#[derive(Clone)]
pub struct UpstreamClient {
    client: Client<HttpConnector, Body>,
}

impl Default for UpstreamClient {
    fn default() -> Self {
        let mut connector = HttpConnector::new();
        connector.set_connect_timeout(Some(Duration::from_secs(2)));
        let client = Client::builder(TokioExecutor::new()).build(connector);
        Self { client }
    }
}

impl UpstreamClient {
    /// Sends the request and returns the response head with a streaming body, or the fault.
    ///
    /// # Errors
    /// [`Fault::Timeout`] when no response head arrives in `timeout`, [`Fault::Unreachable`]
    /// for every other failure.
    pub async fn send(
        &self,
        request: Request<Body>,
        timeout: Duration,
    ) -> Result<Response<Body>, Fault> {
        let call = self.client.request(request);
        match tokio::time::timeout(timeout, call).await {
            Err(_) => Err(Fault::Timeout),
            Ok(Err(_)) => Err(Fault::Unreachable),
            Ok(Ok(response)) => Ok(response.map(Body::new)),
        }
    }
}
