//! Identity service: who is this person, have they proven it, and what may they do.
//! This stage: schema, sessions, sign-in and the session routes (sign-in, sign-out, session).

mod admin_change;
mod admin_users;
mod audit;
mod audit_read;
mod capabilities;
mod cookie;
mod credential_links;
mod export;
mod grants;
pub mod http;
pub mod internal_authz;
pub mod internal_reads;
mod invite;
mod kindle;
mod links;
mod me;
mod password_change;
mod profile_image;
mod query;
mod reply;
pub mod session;
pub mod sign_in;
pub mod sign_out;
mod throttle;
pub mod tickets;
mod totp_manage;
pub mod totp_verify;
mod users;
pub mod vault;

use sqlx::migrate::Migrator;

/// The `identity` database schema, embedded; applied only by the `migrate` one-shot.
pub static MIGRATIONS: Migrator = sqlx::migrate!("./migrations");
