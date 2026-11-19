//! Typed service configuration, parsed once at startup. A bad config stops the
//! process before any listener opens (INV-PLT-003).

mod common;
mod database;
mod error;
mod known;
mod log_level;
mod secret;
mod source;

pub use common::{CommonConfig, ENV_PREFIX};
pub use database::DatabaseConfig;
pub use error::ConfigError;
pub use log_level::LogLevel;
pub use secret::Secret;
pub use source::{ConfigSource, EnvSource, MapSource};
