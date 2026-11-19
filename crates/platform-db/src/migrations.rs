use sqlx::PgPool;
use sqlx::migrate::Migrator;

use crate::DbError;

/// Newest migration version embedded in this binary (0 when there are none).
#[must_use]
pub fn expected_version(migrator: &Migrator) -> i64 {
    migrator
        .iter()
        .filter(|migration| migration.migration_type.is_up_migration())
        .map(|migration| migration.version)
        .max()
        .unwrap_or(0)
}

/// Applies pending migrations; run only by the `migrate` one-shot, never by a service.
///
/// # Errors
/// Returns [`DbError::MigrationFailed`] if any migration fails.
pub async fn apply_migrations(pool: &PgPool, migrator: &Migrator) -> Result<(), DbError> {
    migrator.run(pool).await.map_err(DbError::MigrationFailed)
}

/// Startup check: the applied schema must equal what this binary expects.
///
/// # Errors
/// Returns [`DbError::SchemaVersionMismatch`] on any difference (an unmigrated
/// database counts as version 0) and [`DbError::Unreachable`] if the query fails.
pub async fn ensure_schema_current(pool: &PgPool, migrator: &Migrator) -> Result<(), DbError> {
    let applied = applied_version(pool).await?;
    let expected = expected_version(migrator);
    if applied != expected {
        return Err(DbError::SchemaVersionMismatch { applied, expected });
    }
    Ok(())
}

async fn applied_version(pool: &PgPool) -> Result<i64, DbError> {
    let table_exists: bool =
        sqlx::query_scalar("select to_regclass('_sqlx_migrations') is not null")
            .fetch_one(pool)
            .await
            .map_err(DbError::Unreachable)?;
    if !table_exists {
        return Ok(0);
    }
    sqlx::query_scalar("select coalesce(max(version), 0) from _sqlx_migrations where success")
        .fetch_one(pool)
        .await
        .map_err(DbError::Unreachable)
}
