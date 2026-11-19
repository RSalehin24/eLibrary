use platform_config::LogLevel;
use platform_obs::{LoggingAlreadyStarted, ServiceIdentity, init_logging, service_span};

#[test]
fn logging_starts_once_and_span_is_creatable() {
    assert_eq!(init_logging(LogLevel::Info), Ok(()));
    assert_eq!(init_logging(LogLevel::Info), Err(LoggingAlreadyStarted));
    let span = service_span(ServiceIdentity {
        name: "identity",
        version: "0.1.0",
    });
    let _entered = span.enter();
    tracing::info!("hello");
}
