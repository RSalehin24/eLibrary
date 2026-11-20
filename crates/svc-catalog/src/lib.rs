//! Catalog service: what books exist, who made them and how to find them.
//! This stage: schema and the public read routes (list and detail).

pub mod http;
mod reply;
mod slug;
mod store;

use sqlx::migrate::Migrator;

/// The `catalog` database schema, embedded; applied only by the `migrate` one-shot.
pub static MIGRATIONS: Migrator = sqlx::migrate!("./migrations");
