//! The internal routes end to end with real service tokens against a real Postgres: ignored in
//! a plain `cargo test`; run by `cargo xtask check` (gate Q4).

use std::time::Duration;

use axum::Router;
use axum::body::Body;
use axum::http::header::{AUTHORIZATION, CONTENT_TYPE};
use axum::http::{Request, StatusCode};
use domain_credentials::{Password, PasswordHash, SALT_BYTES};
use platform_config::{MapSource, PublicOrigin};
use platform_service_token::{
    IssueRequest, KeyId, KeyOwner, KeyRing, ServiceName, SigningKey, TokenIssuer, Verifier,
};
use platform_testkit::TestDatabase;
use platform_time::{Clock, SystemClock};
use serde_json::Value;
use sqlx::PgPool;
use svc_identity::vault::{Plain, VaultKey, seal};
use svc_identity::{MIGRATIONS, http};
use tower::ServiceExt;

type Failure = Box<dyn std::error::Error>;

const USER: &str = "00000000-0000-7000-8000-00000000000a";
const PASSWORD: &str = "correct horse battery";

fn key() -> Result<SigningKey, Failure> {
    Ok(SigningKey::new(vec![9; 32])?)
}

fn vault_key() -> Result<VaultKey, Failure> {
    Ok(VaultKey::from_bytes(&[5; 32])?)
}

async fn seed_reader(pool: &PgPool) -> Result<(), Failure> {
    let hash = PasswordHash::create(&Password::parse(PASSWORD)?, &[3; SALT_BYTES])?;
    sqlx::query(
        "insert into users (id, email, display_name, language, status, role, totp_required, created_at, updated_at)
         values ($1::uuid, 'reader@example.org', 'Reader', 'bn', 'active', 'reader', false, now(), now())",
    )
    .bind(USER)
    .execute(pool)
    .await?;
    sqlx::query(
        "insert into credentials (user_id, password_hash, changed_at) values ($1::uuid, $2, now())",
    )
    .bind(USER)
    .bind(hash.as_str())
    .execute(pool)
    .await?;
    Ok(())
}

fn settings() -> Result<http::Settings, Failure> {
    let mut ring = KeyRing::default();
    for caller in ["gateway", "reader", "notify", "catalog"] {
        let owner = KeyOwner {
            service: ServiceName::parse(caller)?,
            id: KeyId(1),
        };
        ring = ring.with(owner, key()?);
    }
    let origin = MapSource::default().with("ELIBRARY_PUBLIC_ORIGIN", "https://library.test");
    Ok(http::Settings {
        key: vault_key()?,
        verifier: Verifier::new(ServiceName::parse("identity")?, ring),
        origin: PublicOrigin::load(&origin)?,
    })
}

async fn app() -> Result<(Router, PgPool), Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    seed_reader(&pool).await?;
    let routes = http::routes_with(pool.clone(), settings()?).map_err(|error| error.to_string())?;
    Ok((routes, pool))
}

fn token_for(caller: &str) -> Result<String, Failure> {
    let issuer = TokenIssuer::new(ServiceName::parse(caller)?, KeyId(1), key()?);
    let request = IssueRequest {
        callee: &ServiceName::parse("identity")?,
        now: SystemClock.now(),
        lifetime: Duration::from_secs(30),
    };
    let token = issuer.issue(request).ok_or("no token")?;
    Ok(token.as_str().to_owned())
}

async fn call(
    app: &Router,
    caller: Option<&str>,
    request: (&str, &str, &str),
) -> Result<(StatusCode, Value), Failure> {
    let (method, path, body) = request;
    let mut builder = Request::builder()
        .method(method)
        .uri(path)
        .header(CONTENT_TYPE, "application/json");
    if let Some(caller) = caller {
        builder = builder.header(AUTHORIZATION, format!("Service {}", token_for(caller)?));
    }
    let response = app
        .clone()
        .oneshot(builder.body(Body::from(body.to_owned()))?)
        .await?;
    let status = response.status();
    let bytes = axum::body::to_bytes(response.into_body(), 64 * 1024).await?;
    Ok((
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    ))
}

fn text<'a>(value: &'a Value, pointer: &str) -> &'a str {
    value
        .pointer(pointer)
        .and_then(Value::as_str)
        .unwrap_or_default()
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_missing_bad_or_wrong_caller_token_is_refused() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let path = format!("/internal/users/{USER}/grant-version");
    let none = call(&app, None, ("GET", &path, "")).await?;
    assert_eq!(
        (none.0, text(&none.1, "/error/code")),
        (StatusCode::UNAUTHORIZED, "service_token_invalid")
    );
    let notify = call(&app, Some("notify"), ("GET", &path, "")).await?;
    assert_eq!(notify.0, StatusCode::FORBIDDEN);
    let reader = call(&app, Some("reader"), ("GET", &path, "")).await?;
    assert_eq!(reader.0, StatusCode::OK);
    assert_eq!(
        reader.1.pointer("/grant_version").and_then(Value::as_i64),
        Some(0)
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn user_info_and_events_are_served_to_their_callers() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    sqlx::query("insert into kindle_addresses (user_id, position, address) values ($1::uuid, 0, 'a@kindle.com')")
        .bind(USER)
        .execute(&pool)
        .await?;
    let user = call(
        &app,
        Some("notify"),
        ("GET", &format!("/internal/users/{USER}"), ""),
    )
    .await?;
    assert_eq!(text(&user.1, "/kindle_addresses/0"), "a@kindle.com");
    let unknown = "/internal/users/00000000-0000-7000-8000-0000000000ee";
    assert_eq!(
        call(&app, Some("notify"), ("GET", unknown, "")).await?.0,
        StatusCode::NOT_FOUND
    );
    let events = call(
        &app,
        Some("reader"),
        ("GET", "/internal/events?after=0&limit=5", ""),
    )
    .await?;
    assert_eq!(events.0, StatusCode::OK);
    assert_eq!(events.1.pointer("/next").and_then(Value::as_i64), Some(0));
    Ok(())
}

async fn queue_invite_mail(pool: &PgPool, token: &str) -> Result<(), Failure> {
    let plain = Plain {
        owner: uuid::Uuid::parse_str(USER)?,
        bytes: token.as_bytes(),
    };
    let sealed = seal(&vault_key()?, plain, &platform_random::OsRandom)?;
    let hex = platform_random::to_hex(&sealed);
    sqlx::query(
        "insert into links (id, user_id, purpose, token_hash, nonce, state, expires_at, request_id, created_at)
         values ('00000000-0000-7000-8000-0000000000c1', $1::uuid, 'invite', '\\x01', '\\x02', 'issued', now() + interval '1 day', 'req-1', now())",
    )
    .bind(USER)
    .execute(pool)
    .await?;
    sqlx::query(
        "insert into email_requests (request_id, kind, user_id, language, link_ref, created_at)
         values ('req-1', 'invite', $1::uuid, 'en', $2, now())",
    )
    .bind(USER)
    .bind(&hex)
    .execute(pool)
    .await?;
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn an_email_request_is_read_once_with_a_link_from_the_public_origin() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let token = "ab".repeat(48);
    queue_invite_mail(&pool, &token).await?;
    let request = ("GET", "/internal/email-requests/req-1", "");
    let first = call(&app, Some("notify"), request).await?;
    assert_eq!(first.0, StatusCode::OK);
    let link = format!("https://library.test/accept-invite?token={token}");
    assert_eq!(text(&first.1, "/link"), link);
    assert_eq!(text(&first.1, "/to"), "reader@example.org");
    assert_eq!(
        call(&app, Some("notify"), request).await?.0,
        StatusCode::NOT_FOUND
    );
    Ok(())
}
