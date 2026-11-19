//! Ingestion service pieces shared by its two binaries: the API (`svc-ingestion`) and the
//! job worker (`svc-ingestion-worker`). Both use the one `ingestion` database.

use sqlx::migrate::Migrator;

/// The `ingestion` database schema, embedded; applied only by the `migrate` one-shot.
pub static MIGRATIONS: Migrator = sqlx::migrate!("./migrations");
