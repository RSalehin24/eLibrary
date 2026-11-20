//! Notify: sends invitation and password mails from pulled events, with retries and a delivery
//! log, so a mail failure never blocks another service. No public route (REQ-NTF-011).

use sqlx::migrate::Migrator;

pub mod config;
pub mod http;
pub mod puller;
pub mod render;
pub mod retry;
pub mod runner;
pub mod sender;
pub mod smtp;
pub mod status;
pub mod transport;

/// The `notify` database schema, embedded; applied only by the `migrate` one-shot.
pub static MIGRATIONS: Migrator = sqlx::migrate!("./migrations");
