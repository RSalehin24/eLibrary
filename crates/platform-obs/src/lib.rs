//! Logging setup shared by all services: one JSON line per event on stdout.

use platform_config::LogLevel;
use tracing::level_filters::LevelFilter;
use tracing::{Level, Span};

/// Who is logging; attached to every line through a root span.
#[derive(Debug, Clone, Copy)]
pub struct ServiceIdentity {
    pub name: &'static str,
    pub version: &'static str,
}

/// Starts JSON logging at `level`. Call once, first thing in `main`.
///
/// # Errors
/// Returns [`LoggingAlreadyStarted`] if a global subscriber is already set.
pub fn init_logging(level: LogLevel) -> Result<(), LoggingAlreadyStarted> {
    tracing_subscriber::fmt()
        .json()
        .with_max_level(level_filter(level))
        .with_current_span(true)
        .with_span_list(false)
        .try_init()
        .map_err(|_| LoggingAlreadyStarted)
}

/// Root span for the process. Instrument `main`'s future and any spawned task
/// with it so every line carries `service` and `version`.
#[must_use]
pub fn service_span(identity: ServiceIdentity) -> Span {
    tracing::span!(
        Level::ERROR,
        "service",
        service = identity.name,
        version = identity.version
    )
}

/// A global logging subscriber was already installed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LoggingAlreadyStarted;

impl std::fmt::Display for LoggingAlreadyStarted {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("logging already started")
    }
}

impl std::error::Error for LoggingAlreadyStarted {}

fn level_filter(level: LogLevel) -> LevelFilter {
    match level {
        LogLevel::Error => LevelFilter::ERROR,
        LogLevel::Warn => LevelFilter::WARN,
        LogLevel::Info => LevelFilter::INFO,
        LogLevel::Debug => LevelFilter::DEBUG,
        LogLevel::Trace => LevelFilter::TRACE,
    }
}
