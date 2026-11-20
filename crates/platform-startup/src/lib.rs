//! The startup sequence every service shares (INV-PLT-003): config, logging, database,
//! schema version, listeners, readiness. A service's `main` only describes itself.

mod error;
mod serve;
mod shutdown;

use axum::Router;
use platform_config::{CommonConfig, DatabaseConfig, EnvSource};
use platform_db::{apply_migrations, connect, ensure_schema_current};
use platform_http::ContractVersion;
use platform_obs::{ServiceIdentity, init_logging, service_span};
use sqlx::PgPool;
use sqlx::migrate::Migrator;
use tracing::Instrument;

pub use error::StartupError;

const MIGRATE_COMMAND: &str = "migrate";

/// Builds routes from the connected pool; a failure stops startup before any listener opens.
pub type DatabaseRoutes = fn(PgPool) -> Result<Router, Box<dyn std::error::Error + Send + Sync>>;

/// What a service says about itself; everything else is shared.
pub struct ServiceSpec {
    pub identity: ServiceIdentity,
    pub contract: ContractVersion,
    /// `None` for a service without a database (the gateway).
    pub migrations: Option<&'static Migrator>,
    pub public_routes: Router,
    /// Routes that need the database pool, built once it is connected and merged into
    /// `public_routes`. `None` for services whose routes use no database.
    pub database_routes: Option<DatabaseRoutes>,
}

/// Runs the service until a listener fails. With a database, `migrate` as the first
/// argument applies migrations and exits instead (the `migrate` one-shot).
///
/// # Errors
/// Any startup check failing stops the process before a listener opens.
pub async fn run(spec: ServiceSpec) -> Result<(), StartupError> {
    let config = CommonConfig::load(&EnvSource)?;
    init_logging(config.log_level())?;
    let span = service_span(spec.identity);
    start(config, spec).instrument(span).await
}

async fn start(config: CommonConfig, spec: ServiceSpec) -> Result<(), StartupError> {
    let Some(migrations) = spec.migrations else {
        let checks = serve::checks_without_database(spec.contract);
        return serve::serve(config, spec.public_routes, checks).await;
    };
    start_with_database(config, spec, migrations).await
}

async fn start_with_database(
    config: CommonConfig,
    spec: ServiceSpec,
    migrations: &Migrator,
) -> Result<(), StartupError> {
    let pool = connect(&DatabaseConfig::load(&EnvSource)?).await?;
    if is_migrate_command() {
        return migrate(&pool, migrations).await;
    }
    ensure_schema_current(&pool, migrations).await?;
    let routes = match spec.database_routes {
        Some(build) => spec
            .public_routes
            .merge(build(pool.clone()).map_err(StartupError::Routes)?),
        None => spec.public_routes,
    };
    serve::serve(
        config,
        routes,
        serve::checks_with_database(spec.contract, pool),
    )
    .await
}

fn is_migrate_command() -> bool {
    std::env::args().nth(1).as_deref() == Some(MIGRATE_COMMAND)
}

async fn migrate(pool: &PgPool, migrations: &Migrator) -> Result<(), StartupError> {
    apply_migrations(pool, migrations).await?;
    tracing::info!("migrations applied");
    Ok(())
}
