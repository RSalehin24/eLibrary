use crate::common::require;
use crate::{ConfigError, ConfigSource, Secret};

/// Reads a secret from the file named by the setting `key`; the value never appears in the
/// environment. Trailing newlines are dropped.
///
/// # Errors
/// [`ConfigError::Missing`] when the setting is absent, [`ConfigError::SecretUnreadable`] when
/// the file cannot be read.
pub fn read_secret_file(
    source: &impl ConfigSource,
    key: &str,
) -> Result<Secret<String>, ConfigError> {
    let path = require(source, key)?;
    std::fs::read_to_string(path)
        .map(|text| Secret::new(text.trim_end().to_owned()))
        .map_err(|_| ConfigError::SecretUnreadable {
            key: key.to_owned(),
        })
}
