use std::sync::atomic::{AtomicU32, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use platform_db::{DbError, apply_migrations};
use sqlx::migrate::Migrator;
use sqlx::postgres::{PgConnectOptions, PgPoolOptions};
use sqlx::{AssertSqlSafe, Connection, PgConnection, PgPool};
use thiserror::Error;

const ENDPOINT_VARIABLE: &str = "TESTKIT_POSTGRES";
const SUPERUSER: &str = "postgres";
const MAX_CONNECTIONS: u32 = 4;

static COUNTER: AtomicU32 = AtomicU32::new(0);

#[derive(Debug, Error)]
pub enum TestkitError {
    #[error("{ENDPOINT_VARIABLE} is not set: run these tests with `cargo xtask check`")]
    NotConfigured,
    #[error("{ENDPOINT_VARIABLE} must look like host:port")]
    BadEndpoint,
    #[error("test database: {0}")]
    Sql(#[from] sqlx::Error),
    #[error("migrations: {0}")]
    Migrations(#[from] DbError),
}

/// A fresh database with the given migrations applied, private to one test.
pub struct TestDatabase {
    pub pool: PgPool,
    pub name: String,
}

impl TestDatabase {
    /// # Errors
    /// When the endpoint is not configured, Postgres is unreachable or a migration fails.
    pub async fn create(migrations: &Migrator) -> Result<Self, TestkitError> {
        let (host, port) = endpoint()?;
        let name = unique_name();
        let admin = PgConnectOptions::new()
            .host(&host)
            .port(port)
            .username(SUPERUSER);
        let mut connection = PgConnection::connect_with(&admin).await?;
        sqlx::query(AssertSqlSafe(format!("create database {name}")))
            .execute(&mut connection)
            .await?;
        let options = admin.database(&name);
        let pool = PgPoolOptions::new()
            .max_connections(MAX_CONNECTIONS)
            .connect_with(options)
            .await?;
        apply_migrations(&pool, migrations).await?;
        Ok(Self { pool, name })
    }
}

fn endpoint() -> Result<(String, u16), TestkitError> {
    let value = std::env::var(ENDPOINT_VARIABLE).map_err(|_| TestkitError::NotConfigured)?;
    let (host, port) = value.rsplit_once(':').ok_or(TestkitError::BadEndpoint)?;
    Ok((
        host.to_owned(),
        port.parse().map_err(|_| TestkitError::BadEndpoint)?,
    ))
}

// why: lowercase letters and digits only, so the name is safe to splice into `create database`.
fn unique_name() -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |elapsed| elapsed.as_nanos());
    let sequence = COUNTER.fetch_add(1, Ordering::Relaxed);
    format!("test_{}_{sequence}_{nanos}", std::process::id())
}
