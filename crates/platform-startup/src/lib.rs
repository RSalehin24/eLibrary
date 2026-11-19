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

/// What a service says about itself; everything else is shared.
pub struct ServiceSpec {
    pub identity: ServiceIdentity,
    pub contract: ContractVersion,
    /// `None` for a service without a database (the gateway).
    pub migrations: Option<&'static Migrator>,
    pub public_routes: Router,
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
    let ServiceSpec {
        contract,
        migrations,
        public_routes,
        ..
    } = spec;
    let Some(migrations) = migrations else {
        return serve::serve(
            config,
            public_routes,
            serve::checks_without_database(contract),
        )
        .await;
    };
    let pool = connect(&DatabaseConfig::load(&EnvSource)?).await?;
    if is_migrate_command() {
        return migrate(&pool, migrations).await;
    }
    ensure_schema_current(&pool, migrations).await?;
    serve::serve(
        config,
        public_routes,
        serve::checks_with_database(contract, pool),
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
