use std::net::AddrParseError;

use thiserror::Error;

/// Why configuration was rejected. Carries the key, never a secret value.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum ConfigError {
    #[error("required setting {key} is missing")]
    Missing { key: String },
    #[error("setting {key} is not a valid socket address: {source}")]
    InvalidAddress { key: String, source: AddrParseError },
    #[error("setting {key} must not use port 0")]
    ZeroPort { key: String },
    #[error("public and internal listeners must differ")]
    ListenersCollide,
    #[error("unknown setting {key}")]
    Unknown { key: String },
}
