//! Typed service configuration, parsed once at startup. A bad config stops the
//! process before any listener opens (INV-PLT-003).

mod common;
mod database;
mod error;
mod known;
mod log_level;
mod peer_keys;
mod public_origin;
mod secret;
mod secret_file;
mod source;

pub use common::{CommonConfig, ENV_PREFIX};
pub use database::DatabaseConfig;
pub use error::ConfigError;
pub use log_level::LogLevel;
pub use peer_keys::{PeerKey, read_own_signing_key, read_peer_keys};
pub use public_origin::PublicOrigin;
pub use secret::Secret;
pub use secret_file::read_secret_file;
pub use source::{ConfigSource, EnvSource, MapSource};
