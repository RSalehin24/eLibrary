//! PostgreSQL access shared by services: pool, readiness and the migration version check.

mod error;
mod migrations;
mod pool;

pub use error::DbError;
pub use migrations::{apply_migrations, ensure_schema_current, expected_version};
pub use pool::{check_ready, connect};
