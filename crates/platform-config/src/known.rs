use crate::{ConfigError, ConfigSource, ENV_PREFIX};

/// The one registry of settings; anything else with the prefix is a typo or a stale deploy.
const KNOWN_KEYS: [&str; 9] = [
    "ELIBRARY_LISTEN_ADDRESS",
    "ELIBRARY_INTERNAL_ADDRESS",
    "ELIBRARY_LOG_LEVEL",
    "ELIBRARY_DATABASE_HOST",
    "ELIBRARY_DATABASE_PORT",
    "ELIBRARY_DATABASE_NAME",
    "ELIBRARY_DATABASE_USER",
    "ELIBRARY_DATABASE_PASSWORD_FILE",
    "ELIBRARY_TOTP_KEY_FILE",
];

pub(crate) fn reject_unknown(source: &impl ConfigSource) -> Result<(), ConfigError> {
    let unknown = source
        .keys_with_prefix(ENV_PREFIX)
        .into_iter()
        .find(|key| !KNOWN_KEYS.contains(&key.as_str()));
    unknown.map_or(Ok(()), |key| Err(ConfigError::Unknown { key }))
}
