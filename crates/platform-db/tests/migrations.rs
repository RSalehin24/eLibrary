use platform_db::expected_version;
use sqlx::migrate::Migrator;

#[test]
fn no_embedded_migrations_means_version_zero() {
    assert_eq!(expected_version(&Migrator::DEFAULT), 0);
}
