//! The internal status routes with real service tokens against a real Postgres: ignored in a
//! plain `cargo test`; run by `cargo xtask check` (gate Q4).

use std::time::Duration;

use axum::Router;
use axum::body::Body;
use axum::http::header::AUTHORIZATION;
use axum::http::{Request, StatusCode};
use platform_service_token::{
    IssueRequest, KeyId, KeyOwner, KeyRing, ServiceName, SigningKey, TokenIssuer, Verifier,
};
use platform_testkit::TestDatabase;
use platform_time::{Clock, SystemClock};
use serde_json::Value;
use sqlx::PgPool;
use svc_notify::{MIGRATIONS, http};
use tower::ServiceExt;

type Failure = Box<dyn std::error::Error>;

const MESSAGE: &str = "00000000-0000-7000-8000-0000000000a1";

fn key() -> Result<SigningKey, Failure> {
    Ok(SigningKey::new(vec![7; 32])?)
}

async fn app() -> Result<(Router, PgPool), Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    let mut ring = KeyRing::default();
    for caller in ["identity", "reader"] {
        let owner = KeyOwner {
            service: ServiceName::parse(caller)?,
            id: KeyId(1),
        };
        ring = ring.with(owner, key()?);
    }
    let verifier = Verifier::new(ServiceName::parse("notify")?, ring);
    Ok((http::routes(pool.clone(), verifier), pool))
}

fn token(caller: &str) -> Result<String, Failure> {
    let issuer = TokenIssuer::new(ServiceName::parse(caller)?, KeyId(1), key()?);
    let request = IssueRequest {
        callee: &ServiceName::parse("notify")?,
        now: SystemClock.now(),
        lifetime: Duration::from_secs(30),
    };
    Ok(issuer.issue(request).ok_or("no token")?.as_str().to_owned())
}

async fn get(
    app: &Router,
    path: &str,
    caller: Option<&str>,
) -> Result<(StatusCode, Value), Failure> {
    let mut builder = Request::get(path);
    if let Some(caller) = caller {
        builder = builder.header(AUTHORIZATION, format!("Service {}", token(caller)?));
    }
    let response = app.clone().oneshot(builder.body(Body::empty())?).await?;
    let status = response.status();
    let bytes = axum::body::to_bytes(response.into_body(), 64 * 1024).await?;
    Ok((
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    ))
}

async fn queue_message(pool: &PgPool) -> Result<(), Failure> {
    sqlx::query(
        "insert into outbox (id, source, event_id, kind, request_id, user_id, language, state, attempts, error_class, next_attempt_at, created_at, updated_at)
         values ($1::uuid, 'identity', $1::uuid, 'invite', 'r-1', $1::uuid, 'en', 'failed', 3, 'permanent', now(), now() - interval '2 minutes', now())",
    )
    .bind(MESSAGE)
    .execute(pool)
    .await?;
    sqlx::query(
        "insert into delivery_log (outbox_id, attempt, status, error_class, masked_address, at)
         values ($1::uuid, 3, 'failed', 'permanent', 'a***@example.org', now())",
    )
    .bind(MESSAGE)
    .execute(pool)
    .await?;
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_message_reports_its_state_with_a_masked_address() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    queue_message(&pool).await?;
    let path = format!("/internal/messages/{MESSAGE}");
    let (status, body) = get(&app, &path, Some("identity")).await?;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        body.pointer("/status").and_then(Value::as_str),
        Some("failed")
    );
    assert_eq!(
        body.pointer("/masked_address").and_then(Value::as_str),
        Some("a***@example.org")
    );
    assert_eq!(
        body.pointer("/error_class").and_then(Value::as_str),
        Some("permanent")
    );
    let unknown = "/internal/messages/00000000-0000-7000-8000-0000000000ee";
    assert_eq!(
        get(&app, unknown, Some("identity")).await?.0,
        StatusCode::NOT_FOUND
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn only_named_services_with_a_valid_token_may_ask() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    queue_message(&pool).await?;
    let path = format!("/internal/messages/{MESSAGE}");
    assert_eq!(get(&app, &path, None).await?.0, StatusCode::UNAUTHORIZED);
    assert_eq!(
        get(&app, &path, Some("reader")).await?.0,
        StatusCode::FORBIDDEN
    );
    let stats = get(&app, "/internal/stats", Some("identity")).await?;
    assert_eq!(stats.1.pointer("/failed").and_then(Value::as_i64), Some(1));
    Ok(())
}
