//! Identity service. Sample stage (P1): the shared startup only, no domain logic yet.

use axum::Router;
use platform_http::ContractVersion;
use platform_obs::ServiceIdentity;
use platform_startup::{ServiceSpec, StartupError, run};
use svc_identity::{MIGRATIONS, http};

#[tokio::main]
async fn main() -> Result<(), StartupError> {
    run(ServiceSpec {
        identity: ServiceIdentity {
            name: "identity",
            version: env!("CARGO_PKG_VERSION"),
        },
        contract: ContractVersion(1),
        migrations: Some(&MIGRATIONS),
        public_routes: Router::new(),
        database_routes: Some(http::routes),
    })
    .await
}
