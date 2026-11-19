//! Typed service configuration, parsed once at startup. A bad config stops the
//! process before any listener opens (INV-PLT-003).

mod common;
mod error;
mod secret;
mod source;

pub use common::{CommonConfig, ENV_PREFIX};
pub use error::ConfigError;
pub use secret::Secret;
pub use source::{ConfigSource, EnvSource, MapSource};
