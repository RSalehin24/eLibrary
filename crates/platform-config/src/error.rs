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
    #[error("setting {key} has an invalid value")]
    InvalidValue { key: String },
    #[error("the secret file named by {key} cannot be read")]
    SecretUnreadable { key: String },
    #[error("unknown setting {key}")]
    Unknown { key: String },
}
