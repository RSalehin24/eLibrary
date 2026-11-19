use platform_config::ConfigError;
use platform_db::DbError;
use platform_obs::LoggingAlreadyStarted;
use thiserror::Error;

/// Why a service did not start or stopped. The process exits non-zero with this message.
#[derive(Debug, Error)]
#[non_exhaustive]
pub enum StartupError {
    #[error(transparent)]
    Config(#[from] ConfigError),
    #[error(transparent)]
    Logging(#[from] LoggingAlreadyStarted),
    #[error(transparent)]
    Database(#[from] DbError),
    #[error("listener failed: {0}")]
    Listener(#[from] std::io::Error),
}
