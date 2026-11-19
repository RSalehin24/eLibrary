//! Identity service. Sample stage (P1): config, listeners, readiness; no domain logic yet.

use axum::Router;
use platform_config::{CommonConfig, EnvSource};
use platform_http::{ContractVersion, Readiness, internal_router};
use tokio::net::TcpListener;

const CONTRACT_VERSION: ContractVersion = ContractVersion(1);

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config = CommonConfig::load(&EnvSource)?;
    let readiness = Readiness::default();
    let public = TcpListener::bind(config.listen_address()).await?;
    let internal = TcpListener::bind(config.internal_address()).await?;
    readiness.mark_ready();
    let internal_app = internal_router(readiness, CONTRACT_VERSION);
    tokio::try_join!(
        axum::serve(public, Router::new()),
        axum::serve(internal, internal_app)
    )?;
    Ok(())
}
