use std::sync::Arc;

use axum::Router;
use platform_config::CommonConfig;
use platform_db::check_ready;
use platform_http::{ContractVersion, DependencyProbe, InternalChecks, Readiness, internal_router};
use sqlx::PgPool;
use tokio::net::TcpListener;

use crate::StartupError;
use crate::shutdown::ShutdownSignal;

pub(crate) fn checks_without_database(contract: ContractVersion) -> InternalChecks {
    InternalChecks::without_dependencies(Readiness::default(), contract)
}

pub(crate) fn checks_with_database(contract: ContractVersion, pool: PgPool) -> InternalChecks {
    InternalChecks {
        readiness: Readiness::default(),
        contract,
        dependencies: database_probe(pool),
    }
}

fn database_probe(pool: PgPool) -> DependencyProbe {
    Arc::new(move || Box::pin(database_is_up(pool.clone())))
}

async fn database_is_up(pool: PgPool) -> bool {
    check_ready(&pool).await.is_ok()
}

/// Opens both listeners, then flips ready (listeners first, INV-PLT-003).
pub(crate) async fn serve(
    config: CommonConfig,
    public_routes: Router,
    checks: InternalChecks,
) -> Result<(), StartupError> {
    let shutdown = ShutdownSignal::install()?;
    let public = TcpListener::bind(config.listen_address()).await?;
    let internal = TcpListener::bind(config.internal_address()).await?;
    let readiness = checks.readiness.clone();
    readiness.mark_ready();
    tracing::info!("ready");
    tokio::try_join!(
        axum::serve(public, public_routes).with_graceful_shutdown(shutdown.clone().wait()),
        axum::serve(internal, internal_router(checks)).with_graceful_shutdown(shutdown.wait())
    )?;
    tracing::info!("stopped");
    Ok(())
}
