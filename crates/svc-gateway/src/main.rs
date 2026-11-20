//! Gateway service. Sample stage (P1): the shared startup only, no domain logic yet (no database).

use axum::Router;
use platform_http::ContractVersion;
use platform_obs::ServiceIdentity;
use platform_startup::{ServiceSpec, StartupError, run};

#[tokio::main]
async fn main() -> Result<(), StartupError> {
    run(ServiceSpec {
        identity: ServiceIdentity {
            name: "gateway",
            version: env!("CARGO_PKG_VERSION"),
        },
        contract: ContractVersion(1),
        migrations: None,
        public_routes: Router::new(),
        database_routes: None,
    })
    .await
}
