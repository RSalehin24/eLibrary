//! The session routes end to end against a real Postgres: ignored in a plain `cargo test`;
//! run by `cargo xtask check` (gate Q4).

use axum::Router;
use axum::body::Body;
use axum::http::header::{CONTENT_TYPE, COOKIE, SET_COOKIE};
use axum::http::{Request, Response, StatusCode};
use domain_credentials::{Password, PasswordHash, SALT_BYTES};
use domain_credentials::{TOTP_STEP_SECONDS, TotpSecret, TotpStep};
use platform_random::OsRandom;
use platform_testkit::TestDatabase;
use platform_time::{Clock, SystemClock};
use serde_json::Value;
use sqlx::PgPool;
use svc_identity::vault::{Plain, VaultKey, seal};
use svc_identity::{MIGRATIONS, http};
use tower::ServiceExt;

type Failure = Box<dyn std::error::Error>;

const PASSWORD: &str = "correct horse battery";
const USER: &str = "00000000-0000-7000-8000-00000000000a";

fn vault_key() -> Result<VaultKey, Failure> {
    Ok(VaultKey::from_bytes(&[5; 32])?)
}

async fn app() -> Result<(Router, PgPool), Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    let hash = PasswordHash::create(&Password::parse(PASSWORD)?, &[3; SALT_BYTES])?;
    sqlx::query(
        "insert into users (id, email, display_name, language, status, role, totp_required, created_at, updated_at)
         values ($1::uuid, 'reader@example.org', 'Reader', 'bn', 'active', 'reader', false, now(), now())",
    )
    .bind(USER)
    .execute(&pool)
    .await?;
    sqlx::query(
        "insert into credentials (user_id, password_hash, changed_at) values ($1::uuid, $2, now())",
    )
    .bind(USER)
    .bind(hash.as_str())
    .execute(&pool)
    .await?;
    let routes =
        http::routes_with_key(pool.clone(), vault_key()?).map_err(|error| error.to_string())?;
    Ok((routes, pool))
}

fn post(path: &str, body: &str, cookie: Option<&str>) -> Result<Request<Body>, Failure> {
    let mut request = Request::post(path).header(CONTENT_TYPE, "application/json");
    if let Some(cookie) = cookie {
        request = request.header(COOKIE, cookie);
    }
    Ok(request.body(Body::from(body.to_owned()))?)
}

async fn json(response: Response<Body>) -> Result<Value, Failure> {
    let bytes = axum::body::to_bytes(response.into_body(), 64 * 1024).await?;
    Ok(serde_json::from_slice(&bytes)?)
}

fn at<'a>(value: &'a Value, pointer: &str) -> &'a str {
    value
        .pointer(pointer)
        .and_then(Value::as_str)
        .unwrap_or_default()
}

fn cookie_pair(response: &Response<Body>) -> Result<String, Failure> {
    let value = response
        .headers()
        .get(SET_COOKIE)
        .ok_or("no cookie")?
        .to_str()?;
    Ok(value.split(';').next().unwrap_or_default().to_owned())
}

const SIGN_IN: &str = "/api/identity/auth/sign-in";
const SESSION: &str = "/api/identity/auth/session";
const SIGN_OUT: &str = "/api/identity/auth/sign-out";

fn credentials(password: &str) -> String {
    format!(r#"{{"email":"Reader@Example.org","password":"{password}"}}"#)
}

async fn signed_in(app: &Router) -> Result<(String, Value), Failure> {
    let response = app
        .clone()
        .oneshot(post(SIGN_IN, &credentials(PASSWORD), None)?)
        .await?;
    assert_eq!(response.status(), StatusCode::OK);
    let set_cookie = response
        .headers()
        .get(SET_COOKIE)
        .ok_or("no cookie")?
        .to_str()?
        .to_owned();
    assert!(set_cookie.contains("HttpOnly") && set_cookie.contains("Secure"));
    Ok((cookie_pair(&response)?, json(response).await?))
}

fn get_session(cookie: &str) -> Result<Request<Body>, Failure> {
    Ok(Request::get(SESSION)
        .header(COOKIE, cookie)
        .body(Body::empty())?)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn sign_in_then_session_then_sign_out() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let (cookie, body) = signed_in(&app).await?;
    assert_eq!(at(&body, "/status"), "active");
    let current = json(app.clone().oneshot(get_session(&cookie)?).await?).await?;
    assert_eq!(at(&current, "/user/email"), "reader@example.org");
    assert_eq!(at(&current, "/csrf_token"), at(&body, "/csrf_token"));
    let out = app
        .clone()
        .oneshot(post(SIGN_OUT, "", Some(&cookie))?)
        .await?;
    assert_eq!(out.status(), StatusCode::NO_CONTENT);
    let after = app.oneshot(get_session(&cookie)?).await?;
    assert_eq!(after.status(), StatusCode::UNAUTHORIZED);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn wrong_and_unknown_credentials_look_alike_and_set_no_cookie() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let wrong = app
        .clone()
        .oneshot(post(SIGN_IN, &credentials("not the password"), None)?)
        .await?;
    let unknown = r#"{"email":"nobody@example.org","password":"not the password"}"#;
    let unknown = app.oneshot(post(SIGN_IN, unknown, None)?).await?;
    assert_eq!(wrong.status(), StatusCode::UNAUTHORIZED);
    assert_eq!(unknown.status(), StatusCode::UNAUTHORIZED);
    assert!(wrong.headers().get(SET_COOKIE).is_none());
    let (wrong, unknown) = (json(wrong).await?, json(unknown).await?);
    assert_eq!(at(&wrong, "/error/code"), "invalid_credentials");
    assert_eq!(at(&wrong, "/error/message"), at(&unknown, "/error/message"));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_request_without_a_cookie_is_unauthenticated() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let get = Request::get(SESSION).body(Body::empty())?;
    let response = app.oneshot(get).await?;
    assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    assert_eq!(at(&json(response).await?, "/error/code"), "unauthenticated");
    Ok(())
}

const SECRET: &[u8] = b"12345678901234567890";

async fn require_totp(pool: &PgPool) -> Result<(), Failure> {
    let user = uuid::Uuid::parse_str(USER)?;
    let sealed = seal(
        &vault_key()?,
        Plain {
            owner: user,
            bytes: SECRET,
        },
        &OsRandom,
    )?;
    sqlx::query("update users set totp_required = true where id = $1")
        .bind(user)
        .execute(pool)
        .await?;
    sqlx::query(
        "insert into totp (user_id, secret_enc, state, confirmed_at) values ($1, $2, 'enabled', now())",
    )
    .bind(user)
    .bind(sealed)
    .execute(pool)
    .await?;
    Ok(())
}

fn current_code() -> Result<String, Failure> {
    let step = SystemClock
        .now()
        .unix_seconds()
        .div_euclid(TOTP_STEP_SECONDS);
    let code = TotpSecret::from_bytes(SECRET.to_vec())?.code_for(TotpStep(u64::try_from(step)?));
    Ok(format!("{code:06}"))
}

fn totp_body(code: &str) -> String {
    format!(r#"{{"code":"{code}"}}"#)
}

async fn pending_cookie(app: &Router) -> Result<String, Failure> {
    let response = app
        .clone()
        .oneshot(post(SIGN_IN, &credentials(PASSWORD), None)?)
        .await?;
    let cookie = cookie_pair(&response)?;
    assert_eq!(at(&json(response).await?, "/status"), "totp_required");
    Ok(cookie)
}

const VERIFY: &str = "/api/identity/auth/totp/verify";

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_pending_session_is_unusable_until_the_code_is_right() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    require_totp(&pool).await?;
    let cookie = pending_cookie(&app).await?;
    let early = app.clone().oneshot(get_session(&cookie)?).await?;
    assert_eq!(early.status(), StatusCode::UNAUTHORIZED);
    let wrong = app
        .clone()
        .oneshot(post(VERIFY, &totp_body("000000"), Some(&cookie))?)
        .await?;
    assert_eq!(wrong.status(), StatusCode::UNPROCESSABLE_ENTITY);
    let right = app
        .clone()
        .oneshot(post(VERIFY, &totp_body(&current_code()?), Some(&cookie))?)
        .await?;
    assert_eq!(right.status(), StatusCode::OK);
    let after = app.oneshot(get_session(&cookie)?).await?;
    assert_eq!(after.status(), StatusCode::OK);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_used_code_cannot_be_replayed_on_a_new_session() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    require_totp(&pool).await?;
    let first = pending_cookie(&app).await?;
    let code = current_code()?;
    let ok = app
        .clone()
        .oneshot(post(VERIFY, &totp_body(&code), Some(&first))?)
        .await?;
    assert_eq!(ok.status(), StatusCode::OK);
    let second = pending_cookie(&app).await?;
    let replay = app
        .oneshot(post(VERIFY, &totp_body(&code), Some(&second))?)
        .await?;
    assert_eq!(replay.status(), StatusCode::UNPROCESSABLE_ENTITY);
    Ok(())
}
