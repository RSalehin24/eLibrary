//! Ingestion worker. Sample stage (P1): the shared startup only; the job loop comes with P6.
//! It has no public routes and no database of its own: it uses the `ingestion` database.

use axum::Router;
use platform_http::ContractVersion;
use platform_obs::ServiceIdentity;
use platform_startup::{ServiceSpec, StartupError, run};
use svc_ingestion::MIGRATIONS;

#[tokio::main]
async fn main() -> Result<(), StartupError> {
    run(ServiceSpec {
        identity: ServiceIdentity {
            name: "ingestion-worker",
            version: env!("CARGO_PKG_VERSION"),
        },
        contract: ContractVersion(1),
        migrations: Some(&MIGRATIONS),
        public_routes: Router::new(),
        database_routes: None,
    })
    .await
}
