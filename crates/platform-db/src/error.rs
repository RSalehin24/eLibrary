use platform_config::ConfigError;
use thiserror::Error;

/// Why a database operation or startup check failed.
#[derive(Debug, Error)]
#[non_exhaustive]
pub enum DbError {
    #[error("database settings: {0}")]
    Config(#[from] ConfigError),
    #[error("database unreachable: {0}")]
    Unreachable(#[source] sqlx::Error),
    #[error("migrations could not be applied: {0}")]
    MigrationFailed(#[source] sqlx::migrate::MigrateError),
    #[error("schema is at version {applied}, this binary expects {expected}")]
    SchemaVersionMismatch { applied: i64, expected: i64 },
}
