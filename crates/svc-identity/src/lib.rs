//! Identity service: who is this person, have they proven it, and what may they do.
//! This stage: schema, sessions and sign-in (no HTTP routes yet).

mod audit;
pub mod session;
pub mod sign_in;
mod throttle;
mod users;

use sqlx::migrate::Migrator;

/// The `identity` database schema, embedded; applied only by the `migrate` one-shot.
pub static MIGRATIONS: Migrator = sqlx::migrate!("./migrations");
