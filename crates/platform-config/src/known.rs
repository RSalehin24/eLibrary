use crate::{ConfigError, ConfigSource, ENV_PREFIX};

/// The one registry of settings; anything else with the prefix is a typo or a stale deploy.
const KNOWN_KEYS: [&str; 23] = [
    "ELIBRARY_LISTEN_ADDRESS",
    "ELIBRARY_INTERNAL_ADDRESS",
    "ELIBRARY_LOG_LEVEL",
    "ELIBRARY_DATABASE_HOST",
    "ELIBRARY_DATABASE_PORT",
    "ELIBRARY_DATABASE_NAME",
    "ELIBRARY_DATABASE_USER",
    "ELIBRARY_DATABASE_PASSWORD_FILE",
    "ELIBRARY_TOTP_KEY_FILE",
    "ELIBRARY_PUBLIC_ORIGIN",
    "ELIBRARY_SERVICE_CALLERS",
    "ELIBRARY_SERVICE_TOKEN_KEY_FILE",
    "ELIBRARY_SERVICE_SIGNING_ID",
    "ELIBRARY_UPSTREAM_IDENTITY",
    "ELIBRARY_SMTP_HOST",
    "ELIBRARY_SMTP_PORT",
    "ELIBRARY_SMTP_FROM",
    "ELIBRARY_SMTP_SECURITY",
    "ELIBRARY_SMTP_USER",
    "ELIBRARY_SMTP_PASSWORD_FILE",
    "ELIBRARY_UPSTREAM_CATALOG",
    "ELIBRARY_UPSTREAM_READER",
    "ELIBRARY_UPSTREAM_INGESTION",
];

pub(crate) fn reject_unknown(source: &impl ConfigSource) -> Result<(), ConfigError> {
    let unknown = source
        .keys_with_prefix(ENV_PREFIX)
        .into_iter()
        .find(|key| !KNOWN_KEYS.contains(&key.as_str()));
    unknown.map_or(Ok(()), |key| Err(ConfigError::Unknown { key }))
}
