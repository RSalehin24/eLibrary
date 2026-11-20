//! Catalog service: the shared startup plus the public read routes.

use axum::Router;
use platform_http::ContractVersion;
use platform_obs::ServiceIdentity;
use platform_startup::{ServiceSpec, StartupError, run};
use svc_catalog::{MIGRATIONS, http};

#[tokio::main]
async fn main() -> Result<(), StartupError> {
    run(ServiceSpec {
        identity: ServiceIdentity {
            name: "catalog",
            version: env!("CARGO_PKG_VERSION"),
        },
        contract: ContractVersion(1),
        migrations: Some(&MIGRATIONS),
        public_routes: Router::new(),
        database_routes: Some(|pool| Ok(http::routes(pool)?)),
    })
    .await
}
