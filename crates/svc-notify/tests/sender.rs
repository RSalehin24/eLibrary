//! The sender against a real Postgres and a stub identity: ignored in a plain `cargo test`;
//! run by `cargo xtask check` (gate Q4).

use std::sync::Arc;
use std::sync::atomic::{AtomicU16, AtomicUsize, Ordering};

use axum::Router;
use axum::extract::State;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::any;
use platform_internal_http::Caller;
use platform_service_token::{KeyId, ServiceName, SigningKey, TokenIssuer};
use platform_testkit::TestDatabase;
use platform_time::Instant;
use sqlx::PgPool;
use svc_notify::MIGRATIONS;
use svc_notify::sender::{Deps, send_due};
use svc_notify::transport::{SendError, SinkTransport};

type Failure = Box<dyn std::error::Error>;

const BASE: i64 = 1_800_000_000;
const ADDRESS: &str = "alice@example.org";

#[derive(Clone)]
struct Stub {
    status: Arc<AtomicU16>,
    hits: Arc<AtomicUsize>,
}

async fn answer(State(stub): State<Stub>) -> Response {
    stub.hits.fetch_add(1, Ordering::SeqCst);
    let code = stub.status.load(Ordering::SeqCst);
    if code == 200 {
        let body = format!(
            r#"{{"kind":"invite","to":"{ADDRESS}","language":"en","link":"https://library.test/invite/TOKEN"}}"#
        );
        return (StatusCode::OK, [("content-type", "application/json")], body).into_response();
    }
    StatusCode::from_u16(code)
        .unwrap_or(StatusCode::INTERNAL_SERVER_ERROR)
        .into_response()
}

struct World {
    pool: PgPool,
    caller: Caller,
    base: String,
    stub: Stub,
    sink: SinkTransport,
}

async fn world(status: u16) -> Result<World, Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    let stub = Stub {
        status: Arc::new(AtomicU16::new(status)),
        hits: Arc::new(AtomicUsize::new(0)),
    };
    let app = Router::new().fallback(any(answer)).with_state(stub.clone());
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await?;
    let base = format!("http://{}", listener.local_addr()?);
    tokio::spawn(async move { axum::serve(listener, app).await });
    let key = SigningKey::new(vec![9; 32])?;
    let issuer = TokenIssuer::new(ServiceName::parse("notify")?, KeyId(1), key);
    Ok(World {
        pool,
        caller: Caller::new(issuer),
        base,
        stub,
        sink: SinkTransport::default(),
    })
}

fn at(offset_seconds: i64) -> Result<Instant, Failure> {
    Instant::from_unix_seconds(BASE + offset_seconds).ok_or_else(|| "bad instant".into())
}

struct Seed<'a> {
    n: i32,
    state: &'a str,
    lease: Option<i64>,
}

async fn insert(pool: &PgPool, seed: Seed<'_>) -> Result<(), Failure> {
    sqlx::query(
        "insert into outbox (id, source, event_id, kind, request_id, user_id, language, state,
                             attempts, next_attempt_at, lease_until, created_at, updated_at)
         values (gen_random_uuid(), 'identity', gen_random_uuid(), 'invite', $1,
                 gen_random_uuid(), 'en', $2, 0, to_timestamp($3::bigint),
                 to_timestamp($4::bigint), now(), now())",
    )
    .bind(format!("req-{}", seed.n))
    .bind(seed.state)
    .bind(BASE)
    .bind(seed.lease.map(|offset| BASE + offset))
    .execute(pool)
    .await?;
    Ok(())
}

async fn run(world: &World, now: Instant) -> Result<usize, Failure> {
    let deps = Deps {
        pool: &world.pool,
        caller: &world.caller,
        identity_base: &world.base,
        transport: &world.sink,
    };
    Ok(send_due(&deps, now).await?)
}

/// Runs until nothing is due; returns how many rows this runner handled.
async fn drain(world: &World) -> Result<usize, Failure> {
    let mut total = 0;
    let mut handled = run(world, at(0)?).await?;
    while handled > 0 {
        total += handled;
        handled = run(world, at(0)?).await?;
    }
    Ok(total)
}

async fn queue(pool: &PgPool, count: i32) -> Result<(), Failure> {
    for n in 0..count {
        insert(
            pool,
            Seed {
                n,
                state: "queued",
                lease: None,
            },
        )
        .await?;
    }
    Ok(())
}

/// Runs `rounds` passes, each far enough apart that a retry is due.
async fn rounds(world: &World, rounds: i64) -> Result<usize, Failure> {
    let mut handled = 0;
    for round in 0..rounds {
        handled += run(world, at(round * 100_000)?).await?;
    }
    Ok(handled)
}

type Summary = (String, i32, Option<String>, i64);

/// State, attempts, error class and `next_attempt_at` (seconds after BASE) of the only row.
async fn only(pool: &PgPool) -> Result<Summary, Failure> {
    let row = sqlx::query_as::<_, Summary>(
        "select state, attempts, error_class, extract(epoch from next_attempt_at)::bigint
           from outbox",
    )
    .fetch_one(pool)
    .await?;
    Ok((row.0, row.1, row.2, row.3 - BASE))
}

fn summary(state: &str, counts: (i32, i64), class: Option<&str>) -> Summary {
    (
        state.to_owned(),
        counts.0,
        class.map(str::to_owned),
        counts.1,
    )
}

async fn log_count(pool: &PgPool) -> Result<i64, Failure> {
    let count = sqlx::query_scalar("select count(*) from delivery_log")
        .fetch_one(pool)
        .await?;
    Ok(count)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn tst_ntf_009_success_sends_once_and_logs_masked() -> Result<(), Failure> {
    let w = world(200).await?;
    insert(
        &w.pool,
        Seed {
            n: 1,
            state: "queued",
            lease: None,
        },
    )
    .await?;
    assert_eq!(run(&w, at(0)?).await?, 1);
    assert_eq!(w.sink.sent().len(), 1);
    assert_eq!(only(&w.pool).await?, summary("sent", (1, 0), None));
    let (status, masked): (String, Option<String>) =
        sqlx::query_as("select status, masked_address from delivery_log")
            .fetch_one(&w.pool)
            .await?;
    assert_eq!(
        (status.as_str(), masked.as_deref()),
        ("sent", Some("a***@example.org"))
    );
    assert_eq!(run(&w, at(10)?).await?, 0, "sent is terminal");
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn tst_ntf_004_no_full_address_or_link_in_the_database() -> Result<(), Failure> {
    let w = world(200).await?;
    insert(
        &w.pool,
        Seed {
            n: 1,
            state: "queued",
            lease: None,
        },
    )
    .await?;
    run(&w, at(0)?).await?;
    let leaks: i64 = sqlx::query_scalar(
        "select (select count(*) from delivery_log where to_jsonb(delivery_log)::text like '%alice@%'
                 or to_jsonb(delivery_log)::text like '%TOKEN%')
              + (select count(*) from outbox where to_jsonb(outbox)::text like '%alice@%'
                 or to_jsonb(outbox)::text like '%TOKEN%')",
    )
    .fetch_one(&w.pool)
    .await?;
    assert_eq!(leaks, 0);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn tst_ntf_008_identity_404_fails_permanently() -> Result<(), Failure> {
    let w = world(404).await?;
    insert(
        &w.pool,
        Seed {
            n: 1,
            state: "queued",
            lease: None,
        },
    )
    .await?;
    run(&w, at(0)?).await?;
    assert_eq!(
        only(&w.pool).await?,
        summary("failed", (1, 0), Some("permanent"))
    );
    assert_eq!(w.sink.sent().len(), 0);
    assert_eq!(log_count(&w.pool).await?, 1);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn tst_ntf_008_identity_503_retries_then_sends() -> Result<(), Failure> {
    let w = world(503).await?;
    insert(
        &w.pool,
        Seed {
            n: 1,
            state: "queued",
            lease: None,
        },
    )
    .await?;
    run(&w, at(0)?).await?;
    assert_eq!(
        only(&w.pool).await?,
        summary("queued", (1, 60), Some("retryable"))
    );
    assert_eq!(run(&w, at(30)?).await?, 0, "not due yet");
    w.stub.status.store(200, Ordering::SeqCst);
    assert_eq!(run(&w, at(61)?).await?, 1);
    assert_eq!(only(&w.pool).await?.0, "sent");
    assert_eq!(w.sink.sent().len(), 1);
    assert_eq!(log_count(&w.pool).await?, 2);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn tst_ntf_008_transport_retryable_then_success() -> Result<(), Failure> {
    let w = world(200).await?;
    insert(
        &w.pool,
        Seed {
            n: 1,
            state: "queued",
            lease: None,
        },
    )
    .await?;
    w.sink.fail_with(Some(SendError::Retryable));
    run(&w, at(0)?).await?;
    assert_eq!(only(&w.pool).await?.0, "queued");
    w.sink.fail_with(None);
    run(&w, at(61)?).await?;
    assert_eq!(only(&w.pool).await?.0, "sent");
    assert_eq!(w.sink.sent().len(), 1);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn tst_ntf_008_transport_permanent_fails_without_retry() -> Result<(), Failure> {
    let w = world(200).await?;
    insert(
        &w.pool,
        Seed {
            n: 1,
            state: "queued",
            lease: None,
        },
    )
    .await?;
    w.sink.fail_with(Some(SendError::Permanent));
    run(&w, at(0)?).await?;
    assert_eq!(
        only(&w.pool).await?,
        summary("failed", (1, 0), Some("permanent"))
    );
    assert_eq!(run(&w, at(100_000)?).await?, 0);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn tst_ntf_008_six_retryable_failures_end_failed() -> Result<(), Failure> {
    let w = world(200).await?;
    insert(
        &w.pool,
        Seed {
            n: 1,
            state: "queued",
            lease: None,
        },
    )
    .await?;
    w.sink.fail_with(Some(SendError::Retryable));
    assert_eq!(rounds(&w, 6).await?, 6);
    assert_eq!(
        only(&w.pool).await?,
        summary("failed", (6, 500_000), Some("retryable"))
    );
    assert_eq!(log_count(&w.pool).await?, 6);
    assert_eq!(run(&w, at(10_000_000)?).await?, 0);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn tst_ntf_010_crashed_lease_is_picked_up() -> Result<(), Failure> {
    let w = world(200).await?;
    insert(
        &w.pool,
        Seed {
            n: 1,
            state: "sending",
            lease: Some(-60),
        },
    )
    .await?;
    assert_eq!(run(&w, at(0)?).await?, 1);
    assert_eq!(only(&w.pool).await?.0, "sent");
    sqlx::query("delete from outbox").execute(&w.pool).await?;
    insert(
        &w.pool,
        Seed {
            n: 2,
            state: "sending",
            lease: Some(600),
        },
    )
    .await?;
    assert_eq!(run(&w, at(0)?).await?, 0, "a live lease is left alone");
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn tst_ntf_010_concurrent_senders_never_double_send() -> Result<(), Failure> {
    let w = world(200).await?;
    queue(&w.pool, 25).await?;
    let (a, b) = tokio::join!(drain(&w), drain(&w));
    assert_eq!(a? + b?, 25);
    assert_eq!(w.sink.sent().len(), 25);
    assert_eq!(w.stub.hits.load(Ordering::SeqCst), 25);
    let odd: i64 =
        sqlx::query_scalar("select count(*) from outbox where attempts <> 1 or state <> 'sent'")
            .fetch_one(&w.pool)
            .await?;
    assert_eq!(odd, 0);
    assert_eq!(log_count(&w.pool).await?, 25);
    Ok(())
}
