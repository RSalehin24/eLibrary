//! Identity service: who is this person, have they proven it, and what may they do.
//! This stage: schema, sessions, sign-in and the session routes (sign-in, sign-out, session).

mod audit;
mod cookie;
pub mod http;
mod reply;
pub mod session;
pub mod sign_in;
pub mod sign_out;
mod throttle;
pub mod totp_verify;
mod users;
pub mod vault;

use sqlx::migrate::Migrator;

/// The `identity` database schema, embedded; applied only by the `migrate` one-shot.
pub static MIGRATIONS: Migrator = sqlx::migrate!("./migrations");
