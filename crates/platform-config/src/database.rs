use std::path::PathBuf;

use crate::common::{read_address_part, require};
use crate::{ConfigError, ConfigSource, Secret};

const HOST_KEY: &str = "ELIBRARY_DATABASE_HOST";
const PORT_KEY: &str = "ELIBRARY_DATABASE_PORT";
const NAME_KEY: &str = "ELIBRARY_DATABASE_NAME";
const USER_KEY: &str = "ELIBRARY_DATABASE_USER";
const PASSWORD_FILE_KEY: &str = "ELIBRARY_DATABASE_PASSWORD_FILE";

/// Connection settings for a service's own database. The password stays in a
/// secret file; it is never part of a URL or an environment variable.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DatabaseConfig {
    pub host: String,
    pub port: u16,
    pub name: String,
    pub user: String,
    password_file: PathBuf,
}

impl DatabaseConfig {
    /// # Errors
    /// Returns the first missing or invalid setting; unknown settings are rejected.
    pub fn load(source: &impl ConfigSource) -> Result<Self, ConfigError> {
        crate::known::reject_unknown(source)?;
        Ok(Self {
            host: require(source, HOST_KEY)?,
            port: read_address_part(&require(source, PORT_KEY)?, PORT_KEY)?,
            name: require(source, NAME_KEY)?,
            user: require(source, USER_KEY)?,
            password_file: PathBuf::from(require(source, PASSWORD_FILE_KEY)?),
        })
    }

    /// # Errors
    /// Returns [`ConfigError::SecretUnreadable`] if the file cannot be read.
    pub fn read_password(&self) -> Result<Secret<String>, ConfigError> {
        std::fs::read_to_string(&self.password_file)
            .map(|text| Secret::new(text.trim_end().to_owned()))
            .map_err(|_| ConfigError::SecretUnreadable {
                key: PASSWORD_FILE_KEY.to_owned(),
            })
    }
}
