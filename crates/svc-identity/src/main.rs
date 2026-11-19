//! Identity service. Sample stage (P1): config, database checks, listeners, readiness;
//! no domain logic yet. `svc-identity migrate` applies migrations and exits.

use axum::Router;
use platform_config::{CommonConfig, DatabaseConfig, EnvSource};
use platform_db::{apply_migrations, connect, ensure_schema_current};
use platform_http::{ContractVersion, Readiness, internal_router};
use platform_obs::{ServiceIdentity, init_logging, service_span};
use sqlx::PgPool;
use sqlx::migrate::Migrator;
use tokio::net::TcpListener;
use tracing::Instrument;

const CONTRACT_VERSION: ContractVersion = ContractVersion(1);
const IDENTITY: ServiceIdentity = ServiceIdentity {
    name: "identity",
    version: env!("CARGO_PKG_VERSION"),
};
const MIGRATE_COMMAND: &str = "migrate";
static MIGRATIONS: Migrator = sqlx::migrate!("./migrations");

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    run().await
}

// why: the `tokio::main` expansion adds nesting levels; real logic lives outside it.
async fn run() -> Result<(), Box<dyn std::error::Error>> {
    let config = CommonConfig::load(&EnvSource)?;
    init_logging(config.log_level())?;
    let database = DatabaseConfig::load(&EnvSource)?;
    let pool = connect(&database).await?;
    if std::env::args().nth(1).as_deref() == Some(MIGRATE_COMMAND) {
        apply_migrations(&pool, &MIGRATIONS).await?;
        tracing::info!("migrations applied");
        return Ok(());
    }
    serve(config, pool).instrument(service_span(IDENTITY)).await
}

async fn serve(config: CommonConfig, pool: PgPool) -> Result<(), Box<dyn std::error::Error>> {
    ensure_schema_current(&pool, &MIGRATIONS).await?;
    let public = TcpListener::bind(config.listen_address()).await?;
    let internal = TcpListener::bind(config.internal_address()).await?;
    let readiness = Readiness::default();
    readiness.mark_ready();
    tracing::info!("ready");
    let internal_app = internal_router(readiness, CONTRACT_VERSION);
    tokio::try_join!(
        axum::serve(public, Router::new()),
        axum::serve(internal, internal_app)
    )?;
    Ok(())
}
