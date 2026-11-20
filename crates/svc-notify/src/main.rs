//! Notify service: mail from pulled events, with retries and a delivery log. Its only HTTP
//! surface is the internal status routes (REQ-NTF-011).

use axum::Router;
use platform_config::EnvSource;
use platform_http::ContractVersion;
use platform_internal_http::Caller;
use platform_obs::ServiceIdentity;
use platform_startup::{ServiceSpec, StartupError, run};
use sqlx::PgPool;
use svc_notify::config::NotifyConfig;
use svc_notify::runner::{self, Loops};
use svc_notify::smtp::{SmtpSettings, SmtpTransport};
use svc_notify::{MIGRATIONS, http};

type BuildError = Box<dyn std::error::Error + Send + Sync>;

/// Starts the mail loop and returns the internal routes; any bad setting stops startup.
fn routes(pool: PgPool) -> Result<Router, BuildError> {
    let config = NotifyConfig::load(&EnvSource)?;
    let transport = SmtpTransport::new(&SmtpSettings::from_source(&EnvSource)?)?;
    let loops = Loops {
        pool: pool.clone(),
        caller: Caller::new(config.issuer),
        identity_base: config.identity_base,
        transport,
    };
    tokio::spawn(runner::run(loops));
    Ok(http::routes(pool, config.verifier))
}

#[tokio::main]
async fn main() -> Result<(), StartupError> {
    run(ServiceSpec {
        identity: ServiceIdentity {
            name: "notify",
            version: env!("CARGO_PKG_VERSION"),
        },
        contract: ContractVersion(1),
        migrations: Some(&MIGRATIONS),
        public_routes: Router::new(),
        database_routes: Some(routes),
    })
    .await
}
