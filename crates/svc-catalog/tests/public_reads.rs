//! The public read routes end to end against a real Postgres (INV-CAT-002, 003, 005): ignored in a
//! plain `cargo test`; run by `cargo xtask check` (gate Q4).

use axum::Router;
use axum::body::Body;
use axum::http::header::{CACHE_CONTROL, LOCATION};
use axum::http::{Request, StatusCode};
use platform_testkit::TestDatabase;
use serde_json::Value;
use sqlx::PgPool;
use svc_catalog::{MIGRATIONS, http};
use tower::ServiceExt;

type Failure = Box<dyn std::error::Error>;

const HASH: &str = "0000000000000000000000000000000000000000000000000000000000000000";

async fn app() -> Result<(Router, PgPool), Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    Ok((http::routes(pool.clone()), pool))
}

/// A published book `n` with one writer; `minutes` orders publication times.
struct Seed<'a> {
    n: u32,
    slug: &'a str,
    minutes: u32,
}

fn seed(n: u32, slug: &str, minutes: u32) -> Seed<'_> {
    Seed { n, slug, minutes }
}

async fn publish(pool: &PgPool, seed: Seed<'_>) -> Result<(), Failure> {
    let mut tx = pool.begin().await?;
    for sql in publish_steps(&seed) {
        sqlx::query(sqlx::AssertSqlSafe(sql))
            .execute(&mut *tx)
            .await?;
    }
    tx.commit().await?;
    Ok(())
}

fn publish_steps(seed: &Seed<'_>) -> [String; 7] {
    let Seed { n, slug, minutes } = seed;
    let book = format!("00000000-0000-7000-8000-0000000000b{n}");
    let version = format!("00000000-0000-7000-8000-0000000000c{n}");
    let agent = format!("00000000-0000-7000-8000-0000000000a{n}");
    let at = format!("now() - interval '{minutes} minutes'");
    [
        format!("insert into books (id, slug, created_at, updated_at) values ('{book}', '{slug}', now(), now())"),
        format!("insert into book_slugs (slug, book_id, created_at) values ('{slug}', '{book}', now())"),
        format!("insert into agents (id, kind, display_name, exact_key) values ('{agent}', 'person', 'Writer {n}', 'w{n}')"),
        format!(
            "insert into book_versions (id, book_id, version_no, state, title, language, summary, build_hash,
                 source_hash, builder_version, created_by, created_at, state_changed_at)
             values ('{version}', '{book}', 1, 'published', 'Title {n}', 'bn', 'About {n}', '{HASH}', '{HASH}', '1', 't', now(), {at})"
        ),
        format!("insert into credits (version_id, agent_id, role, ordinal) values ('{version}', '{agent}', 'writer', 0)"),
        format!(
            "insert into assets (id, version_id, kind, sha256, size_bytes, media_type, storage_path, created_at)
             values (gen_random_uuid(), '{version}', 'epub', '{HASH}', 10, 'application/epub+zip', 'p', now())"
        ),
        format!("update books set current_version_id = '{version}', latest_version_id = '{version}' where id = '{book}'"),
    ]
}

async fn get(app: &Router, path: &str) -> Result<(StatusCode, Option<String>, Value), Failure> {
    let request = Request::builder().uri(path).body(Body::empty())?;
    let response = app.clone().oneshot(request).await?;
    let status = response.status();
    let location = response
        .headers()
        .get(LOCATION)
        .and_then(|value| value.to_str().ok())
        .map(str::to_owned);
    let bytes = axum::body::to_bytes(response.into_body(), 1 << 20).await?;
    let body = serde_json::from_slice(&bytes).unwrap_or(Value::Null);
    Ok((status, location, body))
}

/// The value at a JSON pointer, as text; `Null` and missing both read as `None`.
fn at<'a>(body: &'a Value, pointer: &str) -> Option<&'a str> {
    body.pointer(pointer).and_then(Value::as_str)
}

fn count(body: &Value, pointer: &str) -> Option<usize> {
    body.pointer(pointer)
        .and_then(Value::as_array)
        .map(Vec::len)
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn an_empty_catalog_lists_nothing() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let (status, _, body) = get(&app, "/api/catalog/books").await?;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(count(&body, "/items"), Some(0));
    assert_eq!(at(&body, "/next"), None);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn the_list_is_newest_first_with_contributors_and_cover() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    publish(&pool, seed(1, "old", 30)).await?;
    publish(&pool, seed(2, "new", 10)).await?;
    let (_, _, body) = get(&app, "/api/catalog/books").await?;
    assert_eq!(at(&body, "/items/0/slug"), Some("new"));
    assert_eq!(at(&body, "/items/1/slug"), Some("old"));
    assert_eq!(at(&body, "/items/0/contributors/0/name"), Some("Writer 2"));
    assert_eq!(
        at(&body, "/items/0/cover_url"),
        Some("/api/catalog/books/new/cover")
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn the_list_pages_by_keyset_without_gaps_or_repeats() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    publish(&pool, seed(1, "old", 30)).await?;
    publish(&pool, seed(2, "middle", 20)).await?;
    publish(&pool, seed(3, "new", 10)).await?;
    let (_, _, first) = get(&app, "/api/catalog/books?limit=2").await?;
    assert_eq!(at(&first, "/items/1/slug"), Some("middle"));
    let after = at(&first, "/next").ok_or("no next")?;
    let (_, _, second) = get(&app, &format!("/api/catalog/books?limit=2&after={after}")).await?;
    assert_eq!(count(&second, "/items"), Some(1));
    assert_eq!(at(&second, "/items/0/slug"), Some("old"));
    assert_eq!(at(&second, "/next"), None);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn detail_shows_metadata_and_never_the_source() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    publish(&pool, seed(1, "a-book", 5)).await?;
    sqlx::query(sqlx::AssertSqlSafe(format!(
        "insert into book_sources (book_id, source_url, source_key, first_linked_at)
         values ('00000000-0000-7000-8000-0000000000b1', 'https://source.example/x', '{HASH}', now())"
    )))
    .execute(&pool)
    .await?;
    let (status, _, body) = get(&app, "/api/catalog/books/a-book").await?;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(at(&body, "/title"), Some("Title 1"));
    assert_eq!(body.pointer("/has_preview"), Some(&Value::Bool(false)));
    assert!(!body.to_string().contains("source.example"), "INV-CAT-002");
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn public_reads_carry_the_cache_header() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let request = Request::builder()
        .uri("/api/catalog/books")
        .body(Body::empty())?;
    let response = app.oneshot(request).await?;
    let cache = response
        .headers()
        .get(CACHE_CONTROL)
        .and_then(|v| v.to_str().ok());
    assert_eq!(cache, Some("public, max-age=60"));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn archived_deleted_and_unknown_books_are_the_same_404() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    publish(&pool, seed(1, "archived", 5)).await?;
    publish(&pool, seed(2, "deleted", 5)).await?;
    sqlx::query("update books set current_version_id = null where slug = 'archived'")
        .execute(&pool)
        .await?;
    sqlx::query("update books set deleted_at = now(), deleted_by = id where slug = 'deleted'")
        .execute(&pool)
        .await?;
    let (_, _, list) = get(&app, "/api/catalog/books").await?;
    assert_eq!(count(&list, "/items"), Some(0), "INV-CAT-003");
    assert_not_found(&app, "archived").await?;
    assert_not_found(&app, "deleted").await?;
    assert_not_found(&app, "unknown").await?;
    assert_not_found(&app, "bad%20slug").await
}

async fn assert_not_found(app: &Router, slug: &str) -> Result<(), Failure> {
    let (status, _, body) = get(app, &format!("/api/catalog/books/{slug}")).await?;
    assert_eq!(status, StatusCode::NOT_FOUND, "{slug}");
    assert_eq!(at(&body, "/error/code"), Some("not_found"), "{slug}");
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn an_old_slug_redirects_permanently_to_the_current_one() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    publish(&pool, seed(1, "old-name", 5)).await?;
    sqlx::query("update books set slug = 'new-name' where slug = 'old-name'")
        .execute(&pool)
        .await?;
    sqlx::query(
        "insert into book_slugs (slug, book_id, created_at) select 'new-name', id, now() from books",
    )
    .execute(&pool)
    .await?;
    let (status, location, body) = get(&app, "/api/catalog/books/old-name").await?;
    assert_eq!(status, StatusCode::MOVED_PERMANENTLY);
    assert_eq!(location.as_deref(), Some("/api/catalog/books/new-name"));
    assert_eq!(at(&body, "/redirect_to"), Some("new-name"));
    let (current, _, _) = get(&app, "/api/catalog/books/new-name").await?;
    assert_eq!(current, StatusCode::OK);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn bad_list_parameters_are_a_validation_failure() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    assert_invalid(&app, "limit=0").await?;
    assert_invalid(&app, "limit=101").await?;
    assert_invalid(&app, "after=junk").await?;
    assert_invalid(&app, "sort=title").await?;
    assert_invalid(&app, "q=abc").await
}

async fn assert_invalid(app: &Router, query: &str) -> Result<(), Failure> {
    let (status, _, body) = get(app, &format!("/api/catalog/books?{query}")).await?;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{query}");
    assert_eq!(
        at(&body, "/error/code"),
        Some("validation_failed"),
        "{query}"
    );
    Ok(())
}
