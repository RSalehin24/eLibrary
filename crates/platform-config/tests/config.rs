use platform_config::{CommonConfig, ConfigError, DatabaseConfig, LogLevel, MapSource, Secret};

fn valid() -> MapSource {
    MapSource::default()
        .with("ELIBRARY_LISTEN_ADDRESS", "0.0.0.0:8080")
        .with("ELIBRARY_INTERNAL_ADDRESS", "127.0.0.1:9090")
}

#[test]
fn loads_a_valid_config() -> Result<(), ConfigError> {
    let config = CommonConfig::load(&valid())?;
    assert_eq!(config.listen_address().port(), 8080);
    assert_eq!(config.internal_address().port(), 9090);
    Ok(())
}

#[test]
fn missing_setting_names_the_key() {
    let source = MapSource::default().with("ELIBRARY_LISTEN_ADDRESS", "0.0.0.0:8080");
    assert_eq!(
        CommonConfig::load(&source),
        Err(ConfigError::Missing {
            key: "ELIBRARY_INTERNAL_ADDRESS".to_owned()
        })
    );
}

#[test]
fn unknown_setting_is_rejected() {
    let source = valid().with("ELIBRARY_LISTEN_ADRESS", "typo");
    assert_eq!(
        CommonConfig::load(&source),
        Err(ConfigError::Unknown {
            key: "ELIBRARY_LISTEN_ADRESS".to_owned()
        })
    );
}

#[test]
fn port_zero_and_colliding_listeners_are_rejected() {
    let zero = valid().with("ELIBRARY_LISTEN_ADDRESS", "0.0.0.0:0");
    assert!(matches!(
        CommonConfig::load(&zero),
        Err(ConfigError::ZeroPort { .. })
    ));
    let same = valid().with("ELIBRARY_INTERNAL_ADDRESS", "0.0.0.0:8080");
    assert_eq!(
        CommonConfig::load(&same),
        Err(ConfigError::ListenersCollide)
    );
}

#[test]
fn malformed_address_is_rejected() {
    let source = valid().with("ELIBRARY_LISTEN_ADDRESS", "not-an-address");
    assert!(matches!(
        CommonConfig::load(&source),
        Err(ConfigError::InvalidAddress { .. })
    ));
}

#[test]
fn secret_never_appears_in_debug_output() {
    let secret = Secret::new("hunter2".to_owned());
    assert!(!format!("{secret:?}").contains("hunter2"));
    assert_eq!(secret.expose(), "hunter2");
}

#[test]
fn log_level_defaults_to_info_and_rejects_nonsense() -> Result<(), ConfigError> {
    assert_eq!(CommonConfig::load(&valid())?.log_level(), LogLevel::Info);
    let debug = valid().with("ELIBRARY_LOG_LEVEL", "debug");
    assert_eq!(CommonConfig::load(&debug)?.log_level(), LogLevel::Debug);
    let bad = valid().with("ELIBRARY_LOG_LEVEL", "loud");
    assert!(matches!(
        CommonConfig::load(&bad),
        Err(ConfigError::InvalidValue { .. })
    ));
    Ok(())
}

fn database() -> MapSource {
    MapSource::default()
        .with("ELIBRARY_DATABASE_HOST", "postgres")
        .with("ELIBRARY_DATABASE_PORT", "5432")
        .with("ELIBRARY_DATABASE_NAME", "identity")
        .with("ELIBRARY_DATABASE_USER", "identity")
        .with("ELIBRARY_DATABASE_PASSWORD_FILE", "/nonexistent/secret")
}

#[test]
fn database_config_loads_and_keeps_the_password_out_of_it() -> Result<(), ConfigError> {
    let config = DatabaseConfig::load(&database())?;
    assert_eq!((config.host.as_str(), config.port), ("postgres", 5432));
    assert!(matches!(
        config.read_password(),
        Err(ConfigError::SecretUnreadable { .. })
    ));
    assert!(!format!("{config:?}").contains("hunter2"));
    Ok(())
}

#[test]
fn database_port_must_be_a_nonzero_number() {
    for port in ["0", "abc", "70000"] {
        let source = database().with("ELIBRARY_DATABASE_PORT", port);
        assert!(
            matches!(
                DatabaseConfig::load(&source),
                Err(ConfigError::InvalidValue { .. })
            ),
            "{port}"
        );
    }
}
