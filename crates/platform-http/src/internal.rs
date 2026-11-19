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

#[derive(Clone)]
struct InternalState {
    readiness: Readiness,
    contract: ContractVersion,
}

/// `GET /internal/health` (alive), `/internal/ready` (503 until ready), `/internal/contract`.
pub fn internal_router(readiness: Readiness, contract: ContractVersion) -> Router {
    Router::new()
        .route("/internal/health", get(|| async { StatusCode::OK }))
        .route("/internal/ready", get(ready))
        .route("/internal/contract", get(contract_version))
        .with_state(InternalState {
            readiness,
            contract,
        })
}

async fn ready(State(state): State<InternalState>) -> StatusCode {
    if state.readiness.is_ready() {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    }
}

async fn contract_version(State(state): State<InternalState>) -> Json<ContractVersion> {
    Json(state.contract)
}
