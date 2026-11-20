//! Gateway service: the only door to the backend. No database.

use axum::Router;
use platform_config::EnvSource;
use platform_http::ContractVersion;
use platform_obs::ServiceIdentity;
use platform_startup::{ServiceSpec, StartupError, run};
use svc_gateway::config::GatewayConfig;
use svc_gateway::pipeline::{Gateway, handle};

#[tokio::main]
async fn main() -> Result<(), StartupError> {
    let config = GatewayConfig::load(&EnvSource).map_err(StartupError::Routes)?;
    let gateway = Gateway::new(config);
    run(ServiceSpec {
        identity: ServiceIdentity {
            name: "gateway",
            version: env!("CARGO_PKG_VERSION"),
        },
        contract: ContractVersion(1),
        migrations: None,
        public_routes: Router::new().fallback(handle).with_state(gateway),
        database_routes: None,
    })
    .await
}
