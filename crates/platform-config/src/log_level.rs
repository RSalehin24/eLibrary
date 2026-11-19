use crate::ConfigError;

/// How verbose logs are. Own enum so config does not depend on a logging crate.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum LogLevel {
    Error,
    Warn,
    #[default]
    Info,
    Debug,
    Trace,
}

impl LogLevel {
    pub(crate) fn parse(key: &str, text: &str) -> Result<Self, ConfigError> {
        match text {
            "error" => Ok(Self::Error),
            "warn" => Ok(Self::Warn),
            "info" => Ok(Self::Info),
            "debug" => Ok(Self::Debug),
            "trace" => Ok(Self::Trace),
            _ => Err(ConfigError::InvalidValue {
                key: key.to_owned(),
            }),
        }
    }
}
