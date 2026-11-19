//! HTTP plumbing shared by all services. First piece: the internal-only
//! health, ready and contract endpoints (never routed by Caddy or the gateway).

mod internal;

pub use internal::{ContractVersion, DependencyProbe, InternalChecks, Readiness, internal_router};
