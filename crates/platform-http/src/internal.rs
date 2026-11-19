use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

use axum::extract::State;
use axum::http::StatusCode;
use axum::routing::get;
use axum::{Json, Router};
use serde::Serialize;

/// Wire-contract version a peer reports during the startup handshake.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct ContractVersion(pub u32);

/// Flipped to ready only after startup checks pass and listeners are open.
#[derive(Debug, Clone, Default)]
pub struct Readiness(Arc<AtomicBool>);

impl Readiness {
    pub fn mark_ready(&self) {
        self.0.store(true, Ordering::Release);
    }

    #[must_use]
    pub fn is_ready(&self) -> bool {
        self.0.load(Ordering::Acquire)
    }
}

/// Extra dependency check run on every `/internal/ready` call (for example, a database ping).
pub type DependencyProbe =
    Arc<dyn Fn() -> Pin<Box<dyn Future<Output = bool> + Send>> + Send + Sync>;

/// What the router needs to answer the three internal endpoints.
#[derive(Clone)]
pub struct InternalChecks {
    pub readiness: Readiness,
    pub contract: ContractVersion,
    pub dependencies: DependencyProbe,
}

impl InternalChecks {
    /// Checks with no dependency to probe (services without a database).
    #[must_use]
    pub fn without_dependencies(readiness: Readiness, contract: ContractVersion) -> Self {
        Self {
            readiness,
            contract,
            dependencies: Arc::new(always_up),
        }
    }
}

/// `GET /internal/health` (alive), `/internal/ready` (503 until ready), `/internal/contract`.
pub fn internal_router(checks: InternalChecks) -> Router {
    Router::new()
        .route("/internal/health", get(|| async { StatusCode::OK }))
        .route("/internal/ready", get(ready))
        .route("/internal/contract", get(contract_version))
        .with_state(checks)
}

async fn ready(State(state): State<InternalChecks>) -> StatusCode {
    if state.readiness.is_ready() && (state.dependencies)().await {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    }
}

async fn contract_version(State(state): State<InternalChecks>) -> Json<ContractVersion> {
    Json(state.contract)
}

fn always_up() -> Pin<Box<dyn Future<Output = bool> + Send>> {
    Box::pin(std::future::ready(true))
}
