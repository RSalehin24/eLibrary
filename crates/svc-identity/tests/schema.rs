//! Schema constraints of the identity database (TST-IDN-015 and friends). Ignored in a plain
//! `cargo test`; `cargo xtask check` runs them against the throwaway Postgres (gate Q4).

use platform_testkit::TestDatabase;
use sqlx::migrate::Migrator;
use sqlx::{AssertSqlSafe, PgPool};

static MIGRATIONS: Migrator = sqlx::migrate!("./migrations");

type Failure = Box<dyn std::error::Error>;

const USER_A: &str = "00000000-0000-7000-8000-00000000000a";
const USER_B: &str = "00000000-0000-7000-8000-00000000000b";
const BOOK: &str = "00000000-0000-7000-8000-0000000000b1";
// why: built-in Postgres functions only (no pgcrypto): 32 unique bytes per call.
const RANDOM_HASH: &str = "sha256(gen_random_uuid()::text::bytea)";

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

async fn add_user(pool: &PgPool, id: &str, email: &str) -> Result<(), sqlx::Error> {
    let sql = format!(
        "insert into users (id, email, display_name, language, status, role, created_at, updated_at)
         values ('{id}', '{email}', 'Name', 'bn', 'active', 'reader', now(), now())"
    );
    run(pool, &sql).await
}

fn grant_sql(scope: &str, book: &str, granted_by: &str) -> String {
    format!(
        "insert into grants (id, user_id, scope, book_id, granted_by, reason, created_at)
         values (gen_random_uuid(), '{USER_A}', '{scope}', {book}, '{granted_by}', 'why', now())"
    )
}

fn ticket_sql(minutes: u32) -> String {
    format!(
        "insert into tickets (id, secret_hash, user_id, book_id, version_id, grant_version, issued_at, expires_at)
         values (gen_random_uuid(), {RANDOM_HASH}, '{USER_A}', '{BOOK}', '{BOOK}', 0, now(), now() + interval '{minutes} minutes')"
    )
}

fn link_sql(state: &str) -> String {
    format!(
        "insert into links (id, user_id, purpose, token_hash, nonce, state, expires_at, request_id, created_at)
         values (gen_random_uuid(), '{USER_A}', 'reset', {RANDOM_HASH}, {RANDOM_HASH}, '{state}', now() + interval '1 day', 'r', now())"
    )
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn email_is_unique_ignoring_case_and_enums_are_closed() -> Result<(), Failure> {
    let pool = database().await?;
    add_user(&pool, USER_A, "Reader@Example.org").await?;
    assert!(
        add_user(&pool, USER_B, "reader@example.ORG").await.is_err(),
        "duplicate email by case"
    );
    let bad_role = "insert into users (id, email, display_name, language, status, role, created_at, updated_at)
        values (gen_random_uuid(), 'x@example.org', 'N', 'bn', 'active', 'superuser', now(), now())";
    assert!(run(&pool, bad_role).await.is_err(), "closed role set");
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn grant_checks_reject_unknown_scope_self_grant_book_on_account_scope_and_duplicates()
-> Result<(), Failure> {
    let pool = database().await?;
    add_user(&pool, USER_A, "a@example.org").await?;
    let book = format!("'{BOOK}'");
    assert!(
        run(&pool, &grant_sql("admin_everything", "null", USER_B))
            .await
            .is_err(),
        "unknown scope"
    );
    assert!(
        run(&pool, &grant_sql("download", "null", USER_A))
            .await
            .is_err(),
        "self grant"
    );
    assert!(
        run(&pool, &grant_sql("operate", &book, USER_B))
            .await
            .is_err(),
        "book on account scope"
    );
    run(&pool, &grant_sql("download", &book, USER_B)).await?;
    assert!(
        run(&pool, &grant_sql("download", &book, USER_B))
            .await
            .is_err(),
        "duplicate active grant"
    );
    run(&pool, &grant_sql("download", "null", USER_B)).await?;
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn the_audit_log_is_insert_only_and_old_rows_may_be_pruned() -> Result<(), Failure> {
    let pool = database().await?;
    run(
        &pool,
        "insert into audit_log (at, actor, action) values (now(), 'system', 'test')",
    )
    .await?;
    assert!(
        run(&pool, "update audit_log set action = 'changed'")
            .await
            .is_err(),
        "no update"
    );
    assert!(
        run(&pool, "delete from audit_log").await.is_err(),
        "no delete of recent rows"
    );
    run(&pool, "insert into audit_log (at, actor, action) values (now() - interval '2 years', 'system', 'old')").await?;
    run(
        &pool,
        "delete from audit_log where at < now() - interval '1 year'",
    )
    .await?;
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn tickets_live_at_most_fifteen_minutes_and_links_are_single_issue() -> Result<(), Failure> {
    let pool = database().await?;
    add_user(&pool, USER_A, "a@example.org").await?;
    run(&pool, &ticket_sql(15)).await?;
    assert!(
        run(&pool, &ticket_sql(16)).await.is_err(),
        "ticket longer than 15 minutes"
    );
    run(&pool, &link_sql("issued")).await?;
    assert!(
        run(&pool, &link_sql("issued")).await.is_err(),
        "second issued link for the same purpose"
    );
    run(&pool, &link_sql("consumed")).await?;
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn session_tokens_are_unique_totp_state_matches_confirmation_and_passwords_are_argon2id()
-> Result<(), Failure> {
    let pool = database().await?;
    add_user(&pool, USER_A, "a@example.org").await?;
    let session = format!(
        "insert into sessions (id, token_hash, user_id, state, csrf_hash, created_at, last_seen_at, expires_at)
         values (gen_random_uuid(), '\\x0102', '{USER_A}', 'authenticated', '\\x03', now(), now(), now() + interval '1 hour')"
    );
    run(&pool, &session).await?;
    assert!(run(&pool, &session).await.is_err(), "duplicate token hash");
    let unconfirmed = format!(
        "insert into totp (user_id, secret_enc, state) values ('{USER_A}', '\\x00', 'enabled')"
    );
    assert!(
        run(&pool, &unconfirmed).await.is_err(),
        "enabled needs confirmed_at"
    );
    let weak = format!(
        "insert into credentials (user_id, password_hash, changed_at) values ('{USER_A}', 'md5:abc', now())"
    );
    assert!(run(&pool, &weak).await.is_err(), "only argon2id hashes");
    Ok(())
}
