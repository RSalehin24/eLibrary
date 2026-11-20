//! The puller against a stub identity on a real socket and a real Postgres: ignored in a plain
//! `cargo test`; run by `cargo xtask check` (gate Q4).

use axum::Router;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use platform_internal_http::Caller;
use platform_service_token::{KeyId, ServiceName, SigningKey, TokenIssuer};
use platform_testkit::TestDatabase;
use platform_time::Instant;
use sqlx::PgPool;
use svc_notify::MIGRATIONS;
use svc_notify::puller::{Hub, PullError, Source, pull_all, pull_once};

type Failure = Box<dyn std::error::Error>;

const USER: &str = "00000000-0000-7000-8000-00000000000a";

fn event(cursor: i64, kind: &str, mail: &str) -> String {
    format!(
        r#"{{"cursor":{cursor},"id":"00000000-0000-7000-8000-0000000001{cursor:02}","type":"{kind}","v":1,"subject_id":null,"request_id":null,"extra":1,"payload":{{"request_id":"r-{cursor}","kind":"{mail}","user_id":"{USER}","language":"bn"}},"at":1}}"#
    )
}

fn page(events: &[String], next: i64) -> String {
    format!(r#"{{"events":[{}],"next":{next}}}"#, events.join(","))
}

/// A stub identity answering every `/internal/events` call with the given status and body.
async fn stub(status: StatusCode, body: String) -> Result<String, Failure> {
    let app = Router::new().route(
        "/internal/events",
        get(move || std::future::ready(answer(status, body.clone()))),
    );
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await?;
    let base = format!("http://{}", listener.local_addr()?);
    tokio::spawn(async move { axum::serve(listener, app).await });
    Ok(base)
}

fn answer(status: StatusCode, body: String) -> Response {
    (status, [("content-type", "application/json")], body).into_response()
}

fn caller() -> Result<Caller, Failure> {
    let issuer = TokenIssuer::new(
        ServiceName::parse("notify")?,
        KeyId(1),
        SigningKey::new(vec![9; 32])?,
    );
    Ok(Caller::new(issuer))
}

async fn count(pool: &PgPool, table: &str) -> Result<i64, Failure> {
    let sql = match table {
        "outbox" => "select count(*) from outbox",
        _ => "select cursor from cursors where source = 'identity'",
    };
    let found: Option<i64> = sqlx::query_scalar(sql).fetch_optional(pool).await?;
    Ok(found.unwrap_or(0))
}

fn now() -> Result<Instant, Failure> {
    Instant::from_unix_seconds(1_800_000_000).ok_or_else(|| "bad instant".into())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn inserts_rows_and_advances_the_cursor_then_is_idempotent() -> Result<(), Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    let events = [
        event(1, "email.requested", "invite"),
        event(2, "email.requested", "password_reset"),
    ];
    let base = stub(StatusCode::OK, page(&events, 2)).await?;
    let caller = caller()?;
    let hub = Hub {
        pool: &pool,
        caller: &caller,
    };
    let source = Source {
        name: "identity",
        base: &base,
    };
    let report = pull_once(hub, source, now()?).await?;
    assert_eq!((report.inserted, report.cursor), (2, 2));
    assert_eq!(count(&pool, "outbox").await?, 2);
    let again = pull_once(hub, source, now()?).await?;
    assert_eq!((again.inserted, again.cursor), (0, 2));
    assert_eq!(count(&pool, "outbox").await?, 2);
    let state: String = sqlx::query_scalar("select state from outbox limit 1")
        .fetch_one(&pool)
        .await?;
    assert_eq!(state, "queued");
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn other_event_types_are_skipped_but_the_cursor_advances() -> Result<(), Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    let events = [
        event(1, "grant.changed", "invite"),
        event(2, "email.requested", "bogus"),
    ];
    let base = stub(StatusCode::OK, page(&events, 5)).await?;
    let caller = caller()?;
    let hub = Hub {
        pool: &pool,
        caller: &caller,
    };
    let source = Source {
        name: "identity",
        base: &base,
    };
    let report = pull_once(hub, source, now()?).await?;
    assert_eq!((report.inserted, report.cursor), (0, 5));
    assert_eq!(count(&pool, "outbox").await?, 0);
    assert_eq!(count(&pool, "cursors").await?, 5);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn bad_status_and_garbage_change_nothing() -> Result<(), Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    let caller = caller()?;
    let hub = Hub {
        pool: &pool,
        caller: &caller,
    };
    let base = stub(StatusCode::INTERNAL_SERVER_ERROR, page(&[], 9)).await?;
    let source = Source {
        name: "identity",
        base: &base,
    };
    assert!(matches!(
        pull_once(hub, source, now()?).await,
        Err(PullError::Status(500))
    ));
    let base = stub(StatusCode::OK, "not json".to_owned()).await?;
    let source = Source {
        name: "identity",
        base: &base,
    };
    assert!(matches!(
        pull_once(hub, source, now()?).await,
        Err(PullError::Malformed)
    ));
    assert_eq!(count(&pool, "outbox").await?, 0);
    assert_eq!(count(&pool, "cursors").await?, 0);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn an_unreachable_source_is_an_error() -> Result<(), Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    let caller = caller()?;
    let hub = Hub {
        pool: &pool,
        caller: &caller,
    };
    let source = Source {
        name: "identity",
        base: "http://127.0.0.1:1",
    };
    assert!(matches!(
        pull_once(hub, source, now()?).await,
        Err(PullError::Unreachable)
    ));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn pull_all_stops_when_the_cursor_stops_moving() -> Result<(), Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    let events = [event(1, "email.requested", "password_changed")];
    let base = stub(StatusCode::OK, page(&events, 1)).await?;
    let caller = caller()?;
    let hub = Hub {
        pool: &pool,
        caller: &caller,
    };
    let source = Source {
        name: "identity",
        base: &base,
    };
    assert_eq!(pull_all(hub, source, now()?).await?, 1);
    assert_eq!(count(&pool, "outbox").await?, 1);
    Ok(())
}
