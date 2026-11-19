use std::net::SocketAddr;

use crate::{ConfigError, ConfigSource, LogLevel};

/// Every setting of every service starts with this prefix.
pub const ENV_PREFIX: &str = "ELIBRARY_";
const LISTEN_ADDRESS_KEY: &str = "ELIBRARY_LISTEN_ADDRESS";
const INTERNAL_ADDRESS_KEY: &str = "ELIBRARY_INTERNAL_ADDRESS";
const LOG_LEVEL_KEY: &str = "ELIBRARY_LOG_LEVEL";

/// Settings every service has: the routed listener and the internal-only one
/// (health, ready, contract; never routed by Caddy or the gateway).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommonConfig {
    listen_address: SocketAddr,
    internal_address: SocketAddr,
    log_level: LogLevel,
}

impl CommonConfig {
    /// # Errors
    /// Returns the first problem found; unknown settings are rejected.
    pub fn load(source: &impl ConfigSource) -> Result<Self, ConfigError> {
        crate::known::reject_unknown(source)?;
        let listen_address = read_address(source, LISTEN_ADDRESS_KEY)?;
        let internal_address = read_address(source, INTERNAL_ADDRESS_KEY)?;
        ensure_distinct(listen_address, internal_address)?;
        let log_level = read_log_level(source)?;
        Ok(Self {
            listen_address,
            internal_address,
            log_level,
        })
    }

    #[must_use]
    pub fn listen_address(&self) -> SocketAddr {
        self.listen_address
    }

    #[must_use]
    pub fn internal_address(&self) -> SocketAddr {
        self.internal_address
    }

    #[must_use]
    pub fn log_level(&self) -> LogLevel {
        self.log_level
    }
}

fn read_log_level(source: &impl ConfigSource) -> Result<LogLevel, ConfigError> {
    match source.get(LOG_LEVEL_KEY) {
        Some(text) => LogLevel::parse(LOG_LEVEL_KEY, &text),
        None => Ok(LogLevel::default()),
    }
}

fn ensure_distinct(public: SocketAddr, internal: SocketAddr) -> Result<(), ConfigError> {
    if public == internal {
        return Err(ConfigError::ListenersCollide);
    }
    Ok(())
}

pub(crate) fn read_address(
    source: &impl ConfigSource,
    key: &str,
) -> Result<SocketAddr, ConfigError> {
    let text = require(source, key)?;
    let address: SocketAddr = text.parse().map_err(|source| ConfigError::InvalidAddress {
        key: key.to_owned(),
        source,
    })?;
    if address.port() == 0 {
        return Err(ConfigError::ZeroPort {
            key: key.to_owned(),
        });
    }
    Ok(address)
}

pub(crate) fn require(source: &impl ConfigSource, key: &str) -> Result<String, ConfigError> {
    source.get(key).ok_or_else(|| ConfigError::Missing {
        key: key.to_owned(),
    })
}

pub(crate) fn read_address_part(text: &str, key: &str) -> Result<u16, ConfigError> {
    match text.parse::<u16>() {
        Ok(port) if port != 0 => Ok(port),
        _ => Err(ConfigError::InvalidValue {
            key: key.to_owned(),
        }),
    }
}
