//! Gateway: the only door to the backend. It routes `/api/<service>/*`, asks identity whether a
//! request may proceed, limits rates, and stamps headers. No database, no domain logic
//! (REQ-GWY-008).

pub mod authorize;
pub mod config;
pub mod errors;
pub mod headers;
pub mod limits;
pub mod pipeline;
pub mod routes;
pub mod upstream {
    //! The shared internal HTTP client (moved to `platform-internal-http`).
    pub use platform_internal_http::{Fault, UpstreamClient};
}
