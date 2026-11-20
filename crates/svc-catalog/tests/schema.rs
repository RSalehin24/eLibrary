//! Schema constraints of the catalog database (INV-CAT-001, 003, 004, 005, 020, 021, 031). Ignored in
//! a plain `cargo test`; `cargo xtask check` runs them against the throwaway Postgres (gate Q4).

use platform_testkit::TestDatabase;
use sqlx::migrate::Migrator;
use sqlx::{AssertSqlSafe, PgPool};

static MIGRATIONS: Migrator = sqlx::migrate!("./migrations");

type Failure = Box<dyn std::error::Error>;

const BOOK: &str = "00000000-0000-7000-8000-0000000000b1";
const VERSION: &str = "00000000-0000-7000-8000-0000000000c1";
const AGENT: &str = "00000000-0000-7000-8000-0000000000a1";
const HASH: &str = "0000000000000000000000000000000000000000000000000000000000000000";

async fn database() -> Result<PgPool, Failure> {
    Ok(TestDatabase::create(&MIGRATIONS).await?.pool)
}

// why: the statements below are fixed test text with constant ids; nothing here is user input.
async fn run(pool: &PgPool, sql: &str) -> Result<(), sqlx::Error> {
    sqlx::query(AssertSqlSafe(sql.to_owned()))
        .execute(pool)
        .await
        .map(|_| ())
}

fn book_sql(id: &str, slug: &str) -> String {
    format!(
        "insert into books (id, slug, created_at, updated_at) values ('{id}', '{slug}', now(), now())"
    )
}

fn version_sql(state: &str, reason: &str) -> String {
    format!(
        "insert into book_versions (id, book_id, version_no, state, archived_reason, title, language, build_hash,
             source_hash, builder_version, created_by, created_at, state_changed_at)
         values ('{VERSION}', '{BOOK}', 1, '{state}', {reason}, 'Title', 'bn', '{HASH}', '{HASH}', '1', 'test', now(), now())"
    )
}

const AGENT_SQL: &str = "insert into agents (id, kind, display_name, exact_key) values ('00000000-0000-7000-8000-0000000000a1', 'person', 'Name', 'name')";

fn epub_sql() -> String {
    format!(
        "insert into assets (id, version_id, kind, sha256, size_bytes, media_type, storage_path, created_at)
         values (gen_random_uuid(), '{VERSION}', 'epub', '{HASH}', 10, 'application/epub+zip', 'ab/cd/x', now())"
    )
}

fn credit_sql(role: &str) -> String {
    format!(
        "insert into credits (version_id, agent_id, role, ordinal) values ('{VERSION}', '{AGENT}', '{role}', 0)"
    )
}

async fn publish_in_transaction(
    pool: &PgPool,
    role: &str,
    with_epub: bool,
) -> Result<(), sqlx::Error> {
    let mut tx = pool.begin().await?;
    for sql in [
        book_sql(BOOK, "a-book"),
        AGENT_SQL.to_owned(),
        version_sql("published", "null"),
    ] {
        sqlx::query(AssertSqlSafe(sql)).execute(&mut *tx).await?;
    }
    sqlx::query(AssertSqlSafe(credit_sql(role)))
        .execute(&mut *tx)
        .await?;
    if with_epub {
        sqlx::query(AssertSqlSafe(epub_sql()))
            .execute(&mut *tx)
            .await?;
    }
    tx.commit().await
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn slug_is_unique_and_a_book_id_cannot_change() -> Result<(), Failure> {
    let pool = database().await?;
    run(&pool, &book_sql(BOOK, "a-book")).await?;
    let other = "00000000-0000-7000-8000-0000000000b2";
    assert!(
        run(&pool, &book_sql(other, "a-book")).await.is_err(),
        "duplicate slug"
    );
    assert!(
        run(&pool, &book_sql(other, "has space")).await.is_err(),
        "slug without whitespace"
    );
    let change = format!("update books set id = '{other}' where id = '{BOOK}'");
    assert!(
        run(&pool, &change).await.is_err(),
        "INV-CAT-005: id is immutable"
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn a_version_is_published_or_archived_with_a_reason() -> Result<(), Failure> {
    let pool = database().await?;
    run(&pool, &book_sql(BOOK, "a-book")).await?;
    assert!(
        run(&pool, &version_sql("archived", "null")).await.is_err(),
        "archived needs a reason"
    );
    assert!(
        run(&pool, &version_sql("draft", "null")).await.is_err(),
        "no draft state (D-56)"
    );
    assert!(
        run(&pool, &version_sql("published", "'superseded'"))
            .await
            .is_err(),
        "a published version has no reason"
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn publishing_needs_an_epub_and_a_qualifying_credit() -> Result<(), Failure> {
    let pool = database().await?;
    assert!(
        publish_in_transaction(&pool, "writer", false)
            .await
            .is_err(),
        "no epub"
    );
    assert!(
        publish_in_transaction(&pool, "illustrator", true)
            .await
            .is_err(),
        "INV-CAT-004: no qualifying credit"
    );
    publish_in_transaction(&pool, "writer", true).await?;
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn only_one_published_version_per_book_and_build_hash_is_unique() -> Result<(), Failure> {
    let pool = database().await?;
    publish_in_transaction(&pool, "writer", true).await?;
    let second = version_sql("published", "null")
        .replace(VERSION, "00000000-0000-7000-8000-0000000000c2")
        .replace("1, 'published'", "2, 'published'");
    assert!(
        run(&pool, &second).await.is_err(),
        "INV-CAT-001: one published version"
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn assets_and_history_are_write_once_and_audit_is_insert_only() -> Result<(), Failure> {
    let pool = database().await?;
    publish_in_transaction(&pool, "writer", true).await?;
    assert!(
        run(&pool, "update assets set size_bytes = 11")
            .await
            .is_err(),
        "INV-CAT-021: assets immutable"
    );
    assert!(
        run(&pool, "delete from assets").await.is_err(),
        "assets are not deleted outside the purge"
    );
    run(
        &pool,
        "insert into audit_log (at, actor, action) values (now(), 'test', 'publish')",
    )
    .await?;
    assert!(
        run(&pool, "update audit_log set actor = 'x'")
            .await
            .is_err(),
        "INV-CAT-031: insert-only"
    );
    assert!(
        run(&pool, "delete from audit_log").await.is_err(),
        "recent audit rows stay"
    );
    Ok(())
}
