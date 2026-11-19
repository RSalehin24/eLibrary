use std::time::Duration;

use platform_config::DatabaseConfig;
use sqlx::PgPool;
use sqlx::postgres::{PgConnectOptions, PgPoolOptions};

use crate::DbError;

const MAX_CONNECTIONS: u32 = 5;
const ACQUIRE_TIMEOUT: Duration = Duration::from_secs(5);

/// Connects with the service's own role; the password is read from its secret file.
///
/// # Errors
/// Returns [`DbError::Config`] for a bad setting or unreadable secret, and
/// [`DbError::Unreachable`] when the database does not answer within the timeout.
pub async fn connect(config: &DatabaseConfig) -> Result<PgPool, DbError> {
    let password = config.read_password()?;
    let options = PgConnectOptions::new()
        .host(&config.host)
        .port(config.port)
        .database(&config.name)
        .username(&config.user)
        .password(password.expose());
    PgPoolOptions::new()
        .max_connections(MAX_CONNECTIONS)
        .acquire_timeout(ACQUIRE_TIMEOUT)
        .connect_with(options)
        .await
        .map_err(DbError::Unreachable)
}

/// Cheap round trip for `/internal/ready`.
///
/// # Errors
/// Returns [`DbError::Unreachable`] when the query fails.
pub async fn check_ready(pool: &PgPool) -> Result<(), DbError> {
    sqlx::query("select 1")
        .execute(pool)
        .await
        .map(|_| ())
        .map_err(DbError::Unreachable)
}
