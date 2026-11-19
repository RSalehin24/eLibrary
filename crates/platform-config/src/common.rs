use std::net::SocketAddr;

use crate::{ConfigError, ConfigSource};

/// Every setting of every service starts with this prefix.
pub const ENV_PREFIX: &str = "ELIBRARY_";
const LISTEN_ADDRESS_KEY: &str = "ELIBRARY_LISTEN_ADDRESS";
const INTERNAL_ADDRESS_KEY: &str = "ELIBRARY_INTERNAL_ADDRESS";
const KNOWN_KEYS: [&str; 2] = [LISTEN_ADDRESS_KEY, INTERNAL_ADDRESS_KEY];

/// Settings every service has: the routed listener and the internal-only one
/// (health, ready, contract; never routed by Caddy or the gateway).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommonConfig {
    listen_address: SocketAddr,
    internal_address: SocketAddr,
}

impl CommonConfig {
    /// # Errors
    /// Returns the first problem found; unknown settings are rejected.
    pub fn load(source: &impl ConfigSource) -> Result<Self, ConfigError> {
        reject_unknown(source)?;
        let listen_address = read_address(source, LISTEN_ADDRESS_KEY)?;
        let internal_address = read_address(source, INTERNAL_ADDRESS_KEY)?;
        ensure_distinct(listen_address, internal_address)?;
        Ok(Self {
            listen_address,
            internal_address,
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
}

fn ensure_distinct(public: SocketAddr, internal: SocketAddr) -> Result<(), ConfigError> {
    if public == internal {
        return Err(ConfigError::ListenersCollide);
    }
    Ok(())
}

fn reject_unknown(source: &impl ConfigSource) -> Result<(), ConfigError> {
    let unknown = source
        .keys_with_prefix(ENV_PREFIX)
        .into_iter()
        .find(|key| !KNOWN_KEYS.contains(&key.as_str()));
    unknown.map_or(Ok(()), |key| Err(ConfigError::Unknown { key }))
}

fn read_address(source: &impl ConfigSource, key: &str) -> Result<SocketAddr, ConfigError> {
    let text = source.get(key).ok_or_else(|| ConfigError::Missing {
        key: key.to_owned(),
    })?;
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
