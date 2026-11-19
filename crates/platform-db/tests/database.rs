//! Database tests: ignored in a plain `cargo test`; `cargo xtask check` runs them (gate Q4)
//! against the throwaway Postgres of `deploy/compose/compose.test.yaml`.

use platform_config::{DatabaseConfig, MapSource};
use platform_db::{
    DbError, apply_migrations, check_ready, connect, ensure_schema_current, expected_version,
};
use platform_testkit::TestDatabase;
use sqlx::migrate::Migrator;

static VERSION_ONE: Migrator = sqlx::migrate!("./tests/migrations_v1");
static VERSION_TWO: Migrator = sqlx::migrate!("./tests/migrations_v2");

type Failure = Box<dyn std::error::Error>;

const NEEDS_POSTGRES: &str = "needs the test postgres: run `cargo xtask check`";

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn an_unmigrated_database_is_version_zero_and_fails_the_check() -> Result<(), Failure> {
    let database = TestDatabase::create(&Migrator::DEFAULT).await?;
    let result = ensure_schema_current(&database.pool, &VERSION_TWO).await;
    assert!(
        matches!(
            result,
            Err(DbError::SchemaVersionMismatch {
                applied: 0,
                expected: 2
            })
        ),
        "{result:?}"
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn a_fully_migrated_database_passes_and_an_older_one_fails() -> Result<(), Failure> {
    let current = TestDatabase::create(&VERSION_TWO).await?;
    ensure_schema_current(&current.pool, &VERSION_TWO).await?;
    let behind = TestDatabase::create(&VERSION_ONE).await?;
    let result = ensure_schema_current(&behind.pool, &VERSION_TWO).await;
    assert!(
        matches!(
            result,
            Err(DbError::SchemaVersionMismatch {
                applied: 1,
                expected: 2
            })
        ),
        "{result:?}"
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn applying_migrations_twice_is_a_no_op_and_the_database_answers() -> Result<(), Failure> {
    let database = TestDatabase::create(&VERSION_TWO).await?;
    apply_migrations(&database.pool, &VERSION_TWO).await?;
    check_ready(&database.pool).await?;
    assert_eq!(expected_version(&VERSION_TWO), 2);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn connect_uses_the_service_settings_and_the_password_file() -> Result<(), Failure> {
    let database = TestDatabase::create(&VERSION_ONE).await?;
    let password_file = std::env::temp_dir().join(format!("platform-db-test-{}", database.name));
    std::fs::write(&password_file, "ignored-by-trust-auth\n")?;
    let (host, port) = std::env::var("TESTKIT_POSTGRES")?
        .rsplit_once(':')
        .map(|(h, p)| (h.to_owned(), p.to_owned()))
        .ok_or(NEEDS_POSTGRES)?;
    let source = MapSource::default()
        .with("ELIBRARY_DATABASE_HOST", &host)
        .with("ELIBRARY_DATABASE_PORT", &port)
        .with("ELIBRARY_DATABASE_NAME", &database.name)
        .with("ELIBRARY_DATABASE_USER", "postgres")
        .with(
            "ELIBRARY_DATABASE_PASSWORD_FILE",
            &password_file.to_string_lossy(),
        );
    let pool = connect(&DatabaseConfig::load(&source)?).await?;
    check_ready(&pool).await?;
    std::fs::remove_file(&password_file)?;
    Ok(())
}
