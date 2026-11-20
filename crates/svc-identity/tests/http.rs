//! The session routes end to end against a real Postgres: ignored in a plain `cargo test`;
//! run by `cargo xtask check` (gate Q4).

use axum::Router;
use axum::body::Body;
use axum::http::header::{CONTENT_TYPE, COOKIE, SET_COOKIE};
use axum::http::{Request, Response, StatusCode};
use domain_credentials::{Password, PasswordHash, SALT_BYTES};
use domain_credentials::{TOTP_STEP_SECONDS, TotpSecret, TotpStep};
use platform_config::{MapSource, PublicOrigin};
use platform_random::OsRandom;
use platform_service_token::{KeyRing, ServiceName, Verifier};
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

fn settings() -> Result<http::Settings, Failure> {
    let origin = MapSource::default().with("ELIBRARY_PUBLIC_ORIGIN", "https://library.test");
    Ok(http::Settings {
        key: vault_key()?,
        verifier: Verifier::new(ServiceName::parse("identity")?, KeyRing::default()),
        origin: PublicOrigin::load(&origin)?,
    })
}

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
    let routes = http::routes_with(pool.clone(), settings()?).map_err(|error| error.to_string())?;
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

const ME: &str = "/api/identity/me";

fn patch_me(body: &str, cookie: &str) -> Result<Request<Body>, Failure> {
    Ok(Request::patch(ME)
        .header(CONTENT_TYPE, "application/json")
        .header(COOKIE, cookie)
        .body(Body::from(body.to_owned()))?)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn me_shows_the_profile_and_needs_a_session() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let anonymous = app
        .clone()
        .oneshot(Request::get(ME).body(Body::empty())?)
        .await?;
    assert_eq!(anonymous.status(), StatusCode::UNAUTHORIZED);
    let (cookie, _) = signed_in(&app).await?;
    let request = Request::get(ME)
        .header(COOKIE, &cookie)
        .body(Body::empty())?;
    let me = json(app.oneshot(request).await?).await?;
    assert_eq!(at(&me, "/display_name"), "Reader");
    assert_eq!(at(&me, "/status"), "active");
    assert_eq!(me.pointer("/has_image"), Some(&Value::Bool(false)));
    assert_eq!(me.pointer("/totp_enabled"), Some(&Value::Bool(false)));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn patching_me_changes_only_the_given_fields() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let (cookie, _) = signed_in(&app).await?;
    let response = app
        .clone()
        .oneshot(patch_me(r#"{"display_name":"  Rahim  "}"#, &cookie)?)
        .await?;
    assert_eq!(response.status(), StatusCode::OK);
    let me = json(response).await?;
    assert_eq!(at(&me, "/display_name"), "Rahim");
    assert_eq!(at(&me, "/language"), "bn");
    let revision: i64 = sqlx::query_scalar("select revision from users where id = $1::uuid")
        .bind(USER)
        .fetch_one(&pool)
        .await?;
    assert_eq!(revision, 1);
    Ok(())
}

async fn rejected_field(app: &Router, cookie: &str, body: &str) -> Result<String, Failure> {
    let response = app.clone().oneshot(patch_me(body, cookie)?).await?;
    assert_eq!(
        response.status(),
        StatusCode::UNPROCESSABLE_ENTITY,
        "{body}"
    );
    let error = json(response).await?;
    assert_eq!(at(&error, "/error/code"), "validation_failed");
    Ok(at(&error, "/error/details/fields/0").to_owned())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn patching_me_rejects_bad_fields_with_their_names() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let (cookie, _) = signed_in(&app).await?;
    assert_eq!(rejected_field(&app, &cookie, "{}").await?, "body");
    let blank = r#"{"display_name":"   "}"#;
    assert_eq!(rejected_field(&app, &cookie, blank).await?, "display_name");
    let control = r#"{"display_name":"a\nb"}"#;
    assert_eq!(
        rejected_field(&app, &cookie, control).await?,
        "display_name"
    );
    let language = r#"{"language":"fr"}"#;
    assert_eq!(rejected_field(&app, &cookie, language).await?, "language");
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn capabilities_combine_role_and_live_global_grants() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    sqlx::query(
        "insert into grants (id, user_id, scope, granted_by, reason, created_at)
         values ('00000000-0000-7000-8000-0000000000a1', $1::uuid, 'download', '00000000-0000-7000-8000-0000000000ff', 'test', now()),
                ('00000000-0000-7000-8000-0000000000a2', $1::uuid, 'operate', '00000000-0000-7000-8000-0000000000ff', 'expired', now() - interval '2 days')",
    )
    .bind(USER)
    .execute(&pool)
    .await?;
    sqlx::query("update grants set expires_at = now() - interval '1 day' where scope = 'operate'")
        .execute(&pool)
        .await?;
    let (cookie, _) = signed_in(&app).await?;
    let request = Request::get("/api/identity/me/capabilities")
        .header(COOKIE, &cookie)
        .body(Body::empty())?;
    let set = json(app.oneshot(request).await?).await?;
    assert_eq!(at(&set, "/role"), "reader");
    assert_eq!(at(&set, "/totp"), "off");
    let scopes = strings(&set, "/scopes");
    assert_eq!(scopes, ["browse", "download", "kindle", "preview", "read"]);
    Ok(())
}

fn strings<'a>(value: &'a Value, pointer: &str) -> Vec<&'a str> {
    let list = value.pointer(pointer).and_then(Value::as_array);
    list.into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect()
}

struct Session {
    app: Router,
    cookie: String,
}

impl Session {
    fn request(&self, method: &str, path: &str) -> axum::http::request::Builder {
        Request::builder()
            .method(method)
            .uri(format!("/api/identity/me/totp{path}"))
            .header(CONTENT_TYPE, "application/json")
            .header(COOKIE, &self.cookie)
    }

    async fn post(&self, path: &str, body: &str) -> Result<Response<Body>, Failure> {
        let request = self
            .request("POST", path)
            .body(Body::from(body.to_owned()))?;
        Ok(self.app.clone().oneshot(request).await?)
    }

    async fn status(&self, path: &str, body: &str) -> Result<StatusCode, Failure> {
        Ok(self.post(path, body).await?.status())
    }

    async fn state(&self) -> Result<String, Failure> {
        let request = self.request("GET", "").body(Body::empty())?;
        let body = json(self.app.clone().oneshot(request).await?).await?;
        Ok(at(&body, "/state").to_owned())
    }
}

fn code_at(secret: &str, offset: i64) -> Result<String, Failure> {
    let secret = TotpSecret::from_base32(secret)?;
    let step = SystemClock
        .now()
        .unix_seconds()
        .div_euclid(TOTP_STEP_SECONDS)
        + offset;
    let code = secret.code_for(TotpStep(u64::try_from(step)?));
    Ok(format!("{code:06}"))
}

fn code_body(secret: &str, offset: i64) -> Result<String, Failure> {
    Ok(format!(r#"{{"code":"{}"}}"#, code_at(secret, offset)?))
}

fn reauth_body(secret: &str, offset: i64) -> Result<String, Failure> {
    let code = code_at(secret, offset)?;
    Ok(format!(r#"{{"password":"{PASSWORD}","code":"{code}"}}"#))
}

async fn signed_in_session() -> Result<Session, Failure> {
    let (app, _pool) = app().await?;
    let (cookie, _) = signed_in(&app).await?;
    Ok(Session { app, cookie })
}

/// A session whose TOTP was confirmed with the previous step's code; returns the secret.
async fn enrolled(session: &Session) -> Result<String, Failure> {
    let setup = json(session.post("/setup", "").await?).await?;
    let secret = at(&setup, "/secret").to_owned();
    let confirmed = session.status("/confirm", &code_body(&secret, -1)?).await?;
    assert_eq!(confirmed, StatusCode::OK);
    Ok(secret)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn totp_enrolment_needs_the_right_code() -> Result<(), Failure> {
    let session = signed_in_session().await?;
    assert_eq!(session.state().await?, "off");
    let setup = json(session.post("/setup", "").await?).await?;
    let uri = "otpauth://totp/eLibrary%3Areader%40example.org?";
    assert!(at(&setup, "/provisioning_uri").starts_with(uri));
    assert_eq!(session.state().await?, "pending");
    let wrong = session.status("/confirm", r#"{"code":"000000"}"#).await?;
    assert_eq!(wrong, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(session.state().await?, "pending");
    let right = code_body(at(&setup, "/secret"), -1)?;
    assert_eq!(session.status("/confirm", &right).await?, StatusCode::OK);
    assert_eq!(session.state().await?, "on");
    assert_eq!(
        session.status("/confirm", &right).await?,
        StatusCode::CONFLICT
    );
    assert_eq!(session.status("/setup", "").await?, StatusCode::CONFLICT);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn reveal_needs_password_and_a_fresh_code() -> Result<(), Failure> {
    let session = signed_in_session().await?;
    let secret = enrolled(&session).await?;
    let wrong = format!(
        r#"{{"password":"nope nope nope","code":"{}"}}"#,
        code_at(&secret, 0)?
    );
    assert_eq!(
        session.status("/reveal", &wrong).await?,
        StatusCode::UNAUTHORIZED
    );
    let good = reauth_body(&secret, 0)?;
    let shown = json(session.post("/reveal", &good).await?).await?;
    assert_eq!(at(&shown, "/secret"), secret);
    let replay = session.status("/reveal", &good).await?;
    assert_eq!(replay, StatusCode::UNPROCESSABLE_ENTITY);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn disable_turns_totp_off_unless_the_account_requires_it() -> Result<(), Failure> {
    let session = signed_in_session().await?;
    let secret = enrolled(&session).await?;
    let body = reauth_body(&secret, 1)?;
    assert_eq!(
        session.status("/disable", &body).await?,
        StatusCode::NO_CONTENT
    );
    assert_eq!(session.state().await?, "off");
    Ok(())
}

const PASSWORD_PATH: &str = "/api/identity/me/password";
const NEW_PASSWORD: &str = "a brand new passphrase";

fn password_change(current: &str, new: &str, cookie: &str) -> Result<Request<Body>, Failure> {
    let body = format!(r#"{{"current_password":"{current}","new_password":"{new}"}}"#);
    post(PASSWORD_PATH, &body, Some(cookie))
}

async fn status_for(app: &Router, request: Request<Body>) -> Result<StatusCode, Failure> {
    Ok(app.clone().oneshot(request).await?.status())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn password_change_checks_current_and_policy() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let (cookie, _) = signed_in(&app).await?;
    let wrong = password_change("not the password", NEW_PASSWORD, &cookie)?;
    assert_eq!(status_for(&app, wrong).await?, StatusCode::UNAUTHORIZED);
    let weak = password_change(PASSWORD, "short", &cookie)?;
    let response = app.clone().oneshot(weak).await?;
    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(at(&json(response).await?, "/error/code"), "weak_password");
    let anonymous = post(PASSWORD_PATH, "{}", None)?;
    assert_ne!(status_for(&app, anonymous).await?, StatusCode::NO_CONTENT);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn password_change_keeps_this_session_and_revokes_others() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let (this, _) = signed_in(&app).await?;
    let (other, _) = signed_in(&app).await?;
    let change = password_change(PASSWORD, NEW_PASSWORD, &this)?;
    assert_eq!(status_for(&app, change).await?, StatusCode::NO_CONTENT);
    assert_eq!(status_for(&app, get_session(&this)?).await?, StatusCode::OK);
    let revoked = status_for(&app, get_session(&other)?).await?;
    assert_eq!(revoked, StatusCode::UNAUTHORIZED);
    let old = post(SIGN_IN, &credentials(PASSWORD), None)?;
    assert_eq!(status_for(&app, old).await?, StatusCode::UNAUTHORIZED);
    let new = post(SIGN_IN, &credentials(NEW_PASSWORD), None)?;
    assert_eq!(status_for(&app, new).await?, StatusCode::OK);
    Ok(())
}

const KINDLE: &str = "/api/identity/me/kindle-addresses";

fn put_kindle(body: &str, cookie: &str) -> Result<Request<Body>, Failure> {
    Ok(Request::put(KINDLE)
        .header(CONTENT_TYPE, "application/json")
        .header(COOKIE, cookie)
        .body(Body::from(body.to_owned()))?)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn kindle_addresses_are_replaced_as_a_list() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let (cookie, _) = signed_in(&app).await?;
    let body = r#"{"addresses":["One@Kindle.com","two@kindle.com"]}"#;
    let put = json(app.clone().oneshot(put_kindle(body, &cookie)?).await?).await?;
    assert_eq!(
        strings(&put, "/addresses"),
        ["one@kindle.com", "two@kindle.com"]
    );
    let replaced = r#"{"addresses":["three@kindle.com"]}"#;
    status_for(&app, put_kindle(replaced, &cookie)?).await?;
    let request = Request::get(KINDLE)
        .header(COOKIE, &cookie)
        .body(Body::empty())?;
    let got = json(app.oneshot(request).await?).await?;
    assert_eq!(strings(&got, "/addresses"), ["three@kindle.com"]);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn kindle_addresses_refuse_bad_lists_and_anonymous_callers() -> Result<(), Failure> {
    let (app, _pool) = app().await?;
    let (cookie, _) = signed_in(&app).await?;
    let six = r#"{"addresses":["a@k.com","b@k.com","c@k.com","d@k.com","e@k.com","f@k.com"]}"#;
    let too_many = app.clone().oneshot(put_kindle(six, &cookie)?).await?;
    assert_eq!(too_many.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(at(&json(too_many).await?, "/error/code"), "limit_exceeded");
    let bad = r#"{"addresses":["not an address"]}"#;
    assert_eq!(
        code_of(&app, put_kindle(bad, &cookie)?).await?,
        "validation_failed"
    );
    let twice = r#"{"addresses":["a@k.com","A@k.com"]}"#;
    assert_eq!(
        code_of(&app, put_kindle(twice, &cookie)?).await?,
        "validation_failed"
    );
    let request = Request::get(KINDLE).body(Body::empty())?;
    assert_eq!(status_for(&app, request).await?, StatusCode::UNAUTHORIZED);
    Ok(())
}

async fn code_of(app: &Router, request: Request<Body>) -> Result<String, Failure> {
    let body = json(app.clone().oneshot(request).await?).await?;
    Ok(at(&body, "/error/code").to_owned())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn export_holds_own_data_and_no_secrets() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    sqlx::query(
        "insert into grants (id, user_id, scope, granted_by, reason, created_at)
         values ('00000000-0000-7000-8000-0000000000b1', $1::uuid, 'download', '00000000-0000-7000-8000-0000000000ff', 'private note', now())",
    )
    .bind(USER)
    .execute(&pool)
    .await?;
    let (cookie, _) = signed_in(&app).await?;
    let body = r#"{"addresses":["one@kindle.com"]}"#;
    status_for(&app, put_kindle(body, &cookie)?).await?;
    let request = Request::get("/api/identity/me/export")
        .header(COOKIE, &cookie)
        .body(Body::empty())?;
    let response = app.oneshot(request).await?;
    assert_eq!(response.status(), StatusCode::OK);
    let export = json(response).await?;
    assert_eq!(at(&export, "/profile/email"), "reader@example.org");
    assert_eq!(strings(&export, "/kindle_addresses"), ["one@kindle.com"]);
    assert_eq!(at(&export, "/totp"), "off");
    assert_eq!(at(&export, "/grants/0/scope"), "download");
    let text = export.to_string();
    assert!(!text.contains("argon2") && !text.contains("private note"));
    Ok(())
}

const ADMIN: &str = "00000000-0000-7000-8000-0000000000ad";

async fn admin_cookie(app: &Router, pool: &PgPool) -> Result<String, Failure> {
    let hash = PasswordHash::create(&Password::parse(PASSWORD)?, &[4; SALT_BYTES])?;
    sqlx::query(
        "insert into users (id, email, display_name, language, status, role, totp_required, created_at, updated_at)
         values ($1::uuid, 'admin@example.org', 'Admin', 'en', 'active', 'admin', false, now(), now())",
    )
    .bind(ADMIN)
    .execute(pool)
    .await?;
    sqlx::query(
        "insert into credentials (user_id, password_hash, changed_at) values ($1::uuid, $2, now())",
    )
    .bind(ADMIN)
    .bind(hash.as_str())
    .execute(pool)
    .await?;
    let body = format!(r#"{{"email":"admin@example.org","password":"{PASSWORD}"}}"#);
    let response = app.clone().oneshot(post(SIGN_IN, &body, None)?).await?;
    cookie_pair(&response)
}

fn get_with(path: &str, cookie: &str) -> Result<Request<Body>, Failure> {
    Ok(Request::get(path)
        .header(COOKIE, cookie)
        .body(Body::empty())?)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn user_list_needs_manage_users_and_pages_by_keyset() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let (reader, _) = signed_in(&app).await?;
    let denied = status_for(&app, get_with("/api/identity/users", &reader)?).await?;
    assert_eq!(denied, StatusCode::FORBIDDEN);
    let admin = admin_cookie(&app, &pool).await?;
    let first = json(
        app.clone()
            .oneshot(get_with("/api/identity/users?limit=1", &admin)?)
            .await?,
    )
    .await?;
    assert_eq!(
        first
            .pointer("/items")
            .and_then(Value::as_array)
            .map(Vec::len),
        Some(1)
    );
    let after = at(&first, "/next").to_owned();
    assert_ne!(after, "");
    let second_path = format!("/api/identity/users?limit=1&after={after}");
    let second = json(app.clone().oneshot(get_with(&second_path, &admin)?).await?).await?;
    assert_ne!(at(&second, "/items/0/id"), at(&first, "/items/0/id"));
    assert!(second.pointer("/next").is_some_and(Value::is_null));
    Ok(())
}

async fn get_json(app: &Router, path: &str, cookie: &str) -> Result<Value, Failure> {
    json(app.clone().oneshot(get_with(path, cookie)?).await?).await
}

fn item_count(page: &Value) -> Option<usize> {
    page.pointer("/items")
        .and_then(Value::as_array)
        .map(Vec::len)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn user_list_filters_by_role_text_and_rejects_bad_parameters() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let found = get_json(&app, "/api/identity/users?role=admin&q=ADM", &admin).await?;
    assert_eq!(at(&found, "/items/0/email"), "admin@example.org");
    // a literal percent sign is data, not a wildcard
    let literal = get_json(&app, "/api/identity/users?q=%25", &admin).await?;
    assert_eq!(item_count(&literal), Some(0));
    let bad = get_json(&app, "/api/identity/users?status=gone", &admin).await?;
    assert_eq!(at(&bad, "/error/details/fields/0"), "status");
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn user_detail_shows_grant_summary_and_unknown_is_not_found() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let path = format!("/api/identity/users/{}", reader_id());
    let one = get_json(&app, &path, &admin).await?;
    assert_eq!(at(&one, "/email"), "reader@example.org");
    assert_eq!(
        one.pointer("/active_grants").and_then(Value::as_i64),
        Some(0)
    );
    let missing = "/api/identity/users/00000000-0000-7000-8000-0000000000ee";
    assert_eq!(
        status_for(&app, get_with(missing, &admin)?).await?,
        StatusCode::NOT_FOUND
    );
    Ok(())
}

fn reader_id() -> String {
    contracts_ids::UserId::from_uuid(uuid::Uuid::parse_str(USER).unwrap_or_default()).to_string()
}

fn put_json(path: &str, body: &str, cookie: &str) -> Result<Request<Body>, Failure> {
    Ok(Request::put(path)
        .header(CONTENT_TYPE, "application/json")
        .header(COOKIE, cookie)
        .body(Body::from(body.to_owned()))?)
}

async fn event_types(pool: &PgPool) -> Result<Vec<String>, Failure> {
    Ok(
        sqlx::query_scalar("select type from events order by cursor")
            .fetch_all(pool)
            .await?,
    )
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn suspending_and_reactivating_revokes_sessions_and_emits_events() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let (reader, _) = signed_in(&app).await?;
    let path = format!("/api/identity/users/{}/status", reader_id());
    let suspended = app
        .clone()
        .oneshot(put_json(&path, r#"{"status":"suspended"}"#, &admin)?)
        .await?;
    assert_eq!(suspended.status(), StatusCode::OK);
    assert_eq!(at(&json(suspended).await?, "/status"), "suspended");
    assert_eq!(
        status_for(&app, get_session(&reader)?).await?,
        StatusCode::UNAUTHORIZED
    );
    let sign_in = post(SIGN_IN, &credentials(PASSWORD), None)?;
    assert_eq!(status_for(&app, sign_in).await?, StatusCode::UNAUTHORIZED);
    let active = put_json(&path, r#"{"status":"active"}"#, &admin)?;
    assert_eq!(status_for(&app, active).await?, StatusCode::OK);
    assert_eq!(
        event_types(&pool).await?,
        ["user.disabled", "grant.changed"]
    );
    let version: i64 = sqlx::query_scalar("select grant_version from users where id = $1::uuid")
        .bind(USER)
        .fetch_one(&pool)
        .await?;
    assert_eq!(version, 2);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn status_changes_follow_the_chain_and_never_hit_oneself() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let path = format!("/api/identity/users/{}/status", reader_id());
    let disable = put_json(&path, r#"{"status":"disabled"}"#, &admin)?;
    assert_eq!(status_for(&app, disable).await?, StatusCode::OK);
    let back = put_json(&path, r#"{"status":"active"}"#, &admin)?;
    assert_eq!(status_for(&app, back).await?, StatusCode::CONFLICT);
    let bad = put_json(&path, r#"{"status":"invited"}"#, &admin)?;
    assert_eq!(
        status_for(&app, bad).await?,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    let own = format!(
        "/api/identity/users/{}/status",
        contracts_ids::UserId::from_uuid(uuid::Uuid::parse_str(ADMIN)?)
    );
    let own = put_json(&own, r#"{"status":"suspended"}"#, &admin)?;
    assert_eq!(status_for(&app, own).await?, StatusCode::FORBIDDEN);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn the_last_active_admin_cannot_be_suspended_or_demoted() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    // an operator who was granted manage_users acts on the only admin
    sqlx::query("update users set role = 'operator' where id = $1::uuid")
        .bind(USER)
        .execute(&pool)
        .await?;
    sqlx::query(
        "insert into grants (id, user_id, scope, granted_by, reason, created_at)
         values ('00000000-0000-7000-8000-0000000000c1', $1::uuid, 'manage_users', $2::uuid, 'test', now())",
    )
    .bind(USER)
    .bind(ADMIN)
    .execute(&pool)
    .await?;
    drop(admin);
    let (operator, _) = signed_in(&app).await?;
    let id = contracts_ids::UserId::from_uuid(uuid::Uuid::parse_str(ADMIN)?);
    let suspend = put_json(
        &format!("/api/identity/users/{id}/status"),
        r#"{"status":"suspended"}"#,
        &operator,
    )?;
    assert_eq!(status_for(&app, suspend).await?, StatusCode::FORBIDDEN);
    let demote = put_json(
        &format!("/api/identity/users/{id}/role"),
        r#"{"role":"reader"}"#,
        &operator,
    )?;
    assert_eq!(status_for(&app, demote).await?, StatusCode::FORBIDDEN);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_role_change_takes_effect_in_the_capability_set() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let (reader, _) = signed_in(&app).await?;
    let path = format!("/api/identity/users/{}/role", reader_id());
    let same = put_json(&path, r#"{"role":"reader"}"#, &admin)?;
    assert_eq!(status_for(&app, same).await?, StatusCode::CONFLICT);
    let change = put_json(&path, r#"{"role":"operator"}"#, &admin)?;
    assert_eq!(status_for(&app, change).await?, StatusCode::OK);
    let caps = get_json(&app, "/api/identity/me/capabilities", &reader).await?;
    assert_eq!(at(&caps, "/role"), "operator");
    assert!(strings(&caps, "/scopes").contains(&"operate"));
    assert_eq!(event_types(&pool).await?, ["grant.changed"]);
    Ok(())
}

fn builder(method: &str, path: &str, cookie: &str) -> axum::http::request::Builder {
    Request::builder()
        .method(method)
        .uri(path)
        .header(CONTENT_TYPE, "application/json")
        .header(COOKIE, cookie)
}

/// Sends the request with `body` and returns the status and the JSON body (null when empty).
async fn send(
    app: &Router,
    request: axum::http::request::Builder,
    body: &str,
) -> Result<(StatusCode, Value), Failure> {
    let response = app
        .clone()
        .oneshot(request.body(Body::from(body.to_owned()))?)
        .await?;
    let status = response.status();
    let bytes = axum::body::to_bytes(response.into_body(), 64 * 1024).await?;
    let value = serde_json::from_slice(&bytes).unwrap_or(Value::Null);
    Ok((status, value))
}

fn grant_body(scope: &str, extra: &str) -> String {
    format!(
        r#"{{"user_id":"{}","scope":"{scope}","reason":"for testing"{extra}}}"#,
        reader_id()
    )
}

const GRANTS: &str = "/api/identity/grants";

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn creating_a_grant_widens_the_capability_set_once() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let (reader, _) = signed_in(&app).await?;
    let (status, row) = send(
        &app,
        builder("POST", GRANTS, &admin),
        &grant_body("download", ""),
    )
    .await?;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(at(&row, "/scope"), "download");
    let caps = get_json(&app, "/api/identity/me/capabilities", &reader).await?;
    assert!(strings(&caps, "/scopes").contains(&"download"));
    let (again, error) = send(
        &app,
        builder("POST", GRANTS, &admin),
        &grant_body("download", ""),
    )
    .await?;
    assert_eq!(again, StatusCode::CONFLICT);
    assert_eq!(at(&error, "/error/code"), "duplicate_grant");
    assert_eq!(event_types(&pool).await?, ["grant.changed"]);
    Ok(())
}

async fn grant_status(app: &Router, cookie: &str, body: &str) -> Result<StatusCode, Failure> {
    Ok(send(app, builder("POST", GRANTS, cookie), body).await?.0)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn grant_rules_refuse_unknown_scope_and_book_on_global_scope() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let book = r#","book_id":"00000000-0000-7000-8000-0000000000b0""#;
    let on_global = grant_status(&app, &admin, &grant_body("operate", book)).await?;
    assert_eq!(on_global, StatusCode::UNPROCESSABLE_ENTITY);
    let unknown = grant_status(&app, &admin, &grant_body("root", "")).await?;
    assert_eq!(unknown, StatusCode::UNPROCESSABLE_ENTITY);
    let for_book = grant_status(&app, &admin, &grant_body("read", book)).await?;
    assert_eq!(for_book, StatusCode::CREATED);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn grants_are_never_for_oneself_and_never_already_expired() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let me = contracts_ids::UserId::from_uuid(uuid::Uuid::parse_str(ADMIN)?);
    let own = format!(r#"{{"user_id":"{me}","scope":"read","reason":"x"}}"#);
    assert_eq!(
        grant_status(&app, &admin, &own).await?,
        StatusCode::FORBIDDEN
    );
    let past = grant_body("download", r#","expires_at":1000"#);
    let expired = grant_status(&app, &admin, &past).await?;
    assert_eq!(expired, StatusCode::UNPROCESSABLE_ENTITY);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn editing_needs_the_current_revision_and_revoking_removes_the_scope() -> Result<(), Failure>
{
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let (reader, _) = signed_in(&app).await?;
    let (_, row) = send(
        &app,
        builder("POST", GRANTS, &admin),
        &grant_body("download", ""),
    )
    .await?;
    let path = format!("{GRANTS}/{}", at(&row, "/id"));
    let stale = builder("PATCH", &path, &admin).header("If-Match", "7");
    assert_eq!(
        send(&app, stale, r#"{"active":false}"#).await?.0,
        StatusCode::PRECONDITION_FAILED
    );
    let missing = builder("PATCH", &path, &admin);
    assert_eq!(
        send(&app, missing, r#"{"active":false}"#).await?.0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    let fresh = builder("PATCH", &path, &admin).header("If-Match", "\"0\"");
    let (status, edited) = send(&app, fresh, r#"{"expires_at":null}"#).await?;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(edited.pointer("/revision").and_then(Value::as_i64), Some(1));
    let (status, _) = send(&app, builder("DELETE", &path, &admin), "").await?;
    assert_eq!(status, StatusCode::NO_CONTENT);
    let caps = get_json(&app, "/api/identity/me/capabilities", &reader).await?;
    assert!(!strings(&caps, "/scopes").contains(&"download"));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_failing_batch_changes_nothing() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let batch = "/api/identity/grants/batch";
    let user = reader_id();
    let twice = format!(
        r#"{{"user_id":"{user}","reason":"r","grant":[{{"scope":"download"}},{{"scope":"download"}}]}}"#
    );
    let (status, _) = send(&app, builder("POST", batch, &admin), &twice).await?;
    assert_eq!(status, StatusCode::CONFLICT);
    let count: i64 = sqlx::query_scalar("select count(*) from grants")
        .fetch_one(&pool)
        .await?;
    assert_eq!(count, 0);
    let events: i64 = sqlx::query_scalar("select count(*) from events")
        .fetch_one(&pool)
        .await?;
    assert_eq!(events, 0);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_batch_grants_several_scopes_with_one_event() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let batch = "/api/identity/grants/batch";
    let user = reader_id();
    let two = format!(
        r#"{{"user_id":"{user}","reason":"r","grant":[{{"scope":"download"}},{{"scope":"operate"}}]}}"#
    );
    let (status, body) = send(&app, builder("POST", batch, &admin), &two).await?;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        body.pointer("/granted")
            .and_then(Value::as_array)
            .map(Vec::len),
        Some(2)
    );
    assert_eq!(event_types(&pool).await?, ["grant.changed"]);
    let listed = get_json(
        &app,
        &format!("{GRANTS}?user_id={user}&scope=operate"),
        &admin,
    )
    .await?;
    assert_eq!(item_count(&listed), Some(1));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn an_administrator_edits_a_profile_at_the_current_revision() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let path = format!("/api/identity/users/{}", reader_id());
    let body = r#"{"display_name":"Renamed"}"#;
    let unconditional = send(&app, builder("PATCH", &path, &admin), body).await?;
    assert_eq!(unconditional.0, StatusCode::UNPROCESSABLE_ENTITY);
    let stale = builder("PATCH", &path, &admin).header("If-Match", "9");
    assert_eq!(
        send(&app, stale, body).await?.0,
        StatusCode::PRECONDITION_FAILED
    );
    let fresh = builder("PATCH", &path, &admin).header("If-Match", "0");
    let (status, user) = send(&app, fresh, body).await?;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(at(&user, "/display_name"), "Renamed");
    assert_eq!(user.pointer("/revision").and_then(Value::as_i64), Some(1));
    let unknown = "/api/identity/users/00000000-0000-7000-8000-0000000000ee";
    let missing = builder("PATCH", unknown, &admin).header("If-Match", "0");
    assert_eq!(send(&app, missing, body).await?.0, StatusCode::NOT_FOUND);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn resetting_read_once_clears_the_counter_for_that_book_only() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let (one, two) = (
        "00000000-0000-7000-8000-0000000000b1",
        "00000000-0000-7000-8000-0000000000b2",
    );
    spend_read_once(&pool, one).await?;
    spend_read_once(&pool, two).await?;
    let book = contracts_ids::BookId::from_uuid(uuid::Uuid::parse_str(one)?);
    let path = format!("/api/identity/users/{}/read-once/{book}/reset", reader_id());
    assert_eq!(
        send(&app, builder("POST", &path, &admin), "").await?.0,
        StatusCode::NO_CONTENT
    );
    let left: Vec<uuid::Uuid> = sqlx::query_scalar("select book_id from read_once_uses")
        .fetch_all(&pool)
        .await?;
    assert_eq!(left, [uuid::Uuid::parse_str(two)?]);
    assert_eq!(
        send(&app, builder("POST", &path, &admin), "").await?.0,
        StatusCode::NO_CONTENT
    );
    Ok(())
}

async fn spend_read_once(pool: &PgPool, book: &str) -> Result<(), Failure> {
    sqlx::query(
        "insert into read_once_uses (user_id, book_id, ticket_id, consumed_at)
         values ($1::uuid, $2::uuid, $2::uuid, now())",
    )
    .bind(USER)
    .bind(book)
    .execute(pool)
    .await?;
    Ok(())
}

fn unhex(text: &str) -> Vec<u8> {
    text.as_bytes()
        .chunks(2)
        .filter_map(|pair| std::str::from_utf8(pair).ok())
        .filter_map(|pair| u8::from_str_radix(pair, 16).ok())
        .collect()
}

/// The token of the newest mail request of `kind`, opened the way notify's route will.
async fn mailed_token(pool: &PgPool, kind: &str) -> Result<String, Failure> {
    let row: (uuid::Uuid, String) = sqlx::query_as(
        "select user_id, link_ref from email_requests where kind = $1 order by created_at desc, request_id desc limit 1",
    )
    .bind(kind)
    .fetch_one(pool)
    .await?;
    let bytes = svc_identity::vault::open(&vault_key()?, row.0, &unhex(&row.1))?;
    Ok(String::from_utf8(bytes)?)
}

const INVITE: &str = r#"{"email":"New.Person@Example.org","display_name":"New Person","role":"reader","language":"en"}"#;
const NEW_EMAIL_CREDENTIALS: &str =
    r#"{"email":"new.person@example.org","password":"a brand new passphrase"}"#;

async fn invited_app() -> Result<(Router, PgPool, String), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let (status, body) = send(&app, builder("POST", "/api/identity/users", &admin), INVITE).await?;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(at(&body, "/status"), "invited");
    Ok((app, pool, admin))
}

async fn accept(app: &Router, token: &str, password: &str) -> Result<(StatusCode, Value), Failure> {
    let body = format!(r#"{{"token":"{token}","password":"{password}"}}"#);
    let request =
        Request::post("/api/identity/invites/accept").header(CONTENT_TYPE, "application/json");
    send(app, request, &body).await
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn an_invitation_queues_one_mail_without_address_or_link_in_the_event() -> Result<(), Failure>
{
    let (app, pool, admin) = invited_app().await?;
    assert_eq!(event_types(&pool).await?, ["email.requested"]);
    let payload: Value = sqlx::query_scalar("select payload from events")
        .fetch_one(&pool)
        .await?;
    let text = payload.to_string();
    assert!(!text.contains("example.org") && !text.contains(&mailed_token(&pool, "invite").await?));
    let again = send(&app, builder("POST", "/api/identity/users", &admin), INVITE).await?;
    assert_eq!(at(&again.1, "/error/code"), "email_taken");
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn accepting_an_invitation_activates_the_account_once() -> Result<(), Failure> {
    let (app, pool, _admin) = invited_app().await?;
    let token = mailed_token(&pool, "invite").await?;
    let weak = accept(&app, &token, "short").await?;
    assert_eq!(at(&weak.1, "/error/code"), "weak_password");
    let (status, body) = accept(&app, &token, NEW_PASSWORD).await?;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(at(&body, "/status"), "active");
    let sign_in = post(SIGN_IN, NEW_EMAIL_CREDENTIALS, None)?;
    assert_eq!(status_for(&app, sign_in).await?, StatusCode::OK);
    let reuse = accept(&app, &token, NEW_PASSWORD).await?;
    assert_eq!(
        (reuse.0, at(&reuse.1, "/error/code")),
        (StatusCode::GONE, "link_invalid")
    );
    let unknown = accept(&app, &"0".repeat(96), NEW_PASSWORD).await?;
    assert_eq!(unknown.0, StatusCode::GONE);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn resending_an_invitation_supersedes_the_older_link() -> Result<(), Failure> {
    let (app, pool, admin) = invited_app().await?;
    let old = mailed_token(&pool, "invite").await?;
    let id: uuid::Uuid = sqlx::query_scalar("select id from users where status = 'invited'")
        .fetch_one(&pool)
        .await?;
    let path = format!(
        "/api/identity/users/{}/resend-invite",
        contracts_ids::UserId::from_uuid(id)
    );
    assert_eq!(
        send(&app, builder("POST", &path, &admin), "").await?.0,
        StatusCode::NO_CONTENT
    );
    assert_eq!(accept(&app, &old, NEW_PASSWORD).await?.0, StatusCode::GONE);
    let fresh = mailed_token(&pool, "invite").await?;
    assert_eq!(accept(&app, &fresh, NEW_PASSWORD).await?.0, StatusCode::OK);
    let active_again = send(&app, builder("POST", &path, &admin), "").await?;
    assert_eq!(active_again.0, StatusCode::CONFLICT);
    Ok(())
}

async fn request_reset(app: &Router, email: &str) -> Result<StatusCode, Failure> {
    let body = format!(r#"{{"email":"{email}"}}"#);
    let request = Request::post("/api/identity/password-reset/request")
        .header(CONTENT_TYPE, "application/json");
    Ok(send(app, request, &body).await?.0)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_reset_request_answers_alike_and_mails_only_known_accounts() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    assert_eq!(
        request_reset(&app, "nobody@example.org").await?,
        StatusCode::ACCEPTED
    );
    let none: i64 = sqlx::query_scalar("select count(*) from email_requests")
        .fetch_one(&pool)
        .await?;
    assert_eq!(none, 0);
    assert_eq!(
        request_reset(&app, "Reader@Example.org").await?,
        StatusCode::ACCEPTED
    );
    let kinds: Vec<String> = sqlx::query_scalar("select kind from email_requests")
        .fetch_all(&pool)
        .await?;
    assert_eq!(kinds, ["password_reset"]);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn confirming_a_reset_sets_the_password_and_ends_sessions() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let (session, _) = signed_in(&app).await?;
    request_reset(&app, "reader@example.org").await?;
    let token = mailed_token(&pool, "password_reset").await?;
    assert_eq!(
        status_for(&app, reset_confirm(&token, "short")?).await?,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    assert_eq!(
        status_for(&app, reset_confirm(&token, NEW_PASSWORD)?).await?,
        StatusCode::OK
    );
    assert_eq!(
        status_for(&app, get_session(&session)?).await?,
        StatusCode::UNAUTHORIZED
    );
    let old = post(SIGN_IN, &credentials(PASSWORD), None)?;
    assert_eq!(status_for(&app, old).await?, StatusCode::UNAUTHORIZED);
    let new = post(SIGN_IN, &credentials(NEW_PASSWORD), None)?;
    assert_eq!(status_for(&app, new).await?, StatusCode::OK);
    assert_eq!(
        status_for(&app, reset_confirm(&token, NEW_PASSWORD)?).await?,
        StatusCode::GONE
    );
    Ok(())
}

fn reset_confirm(token: &str, password: &str) -> Result<Request<Body>, Failure> {
    let body = format!(r#"{{"token":"{token}","password":"{password}"}}"#);
    post("/api/identity/password-reset/confirm", &body, None)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn deleting_an_account_removes_it_and_announces_user_deleted() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let (reader, _) = signed_in(&app).await?;
    let path = format!("/api/identity/users/{}", reader_id());
    assert_eq!(
        send(&app, builder("DELETE", &path, &admin), "").await?.0,
        StatusCode::NO_CONTENT
    );
    assert_eq!(
        status_for(&app, get_session(&reader)?).await?,
        StatusCode::UNAUTHORIZED
    );
    let left: i64 = sqlx::query_scalar("select count(*) from users where id = $1::uuid")
        .bind(USER)
        .fetch_one(&pool)
        .await?;
    assert_eq!(left, 0);
    assert_eq!(event_types(&pool).await?, ["user.deleted"]);
    assert_eq!(
        send(&app, builder("DELETE", &path, &admin), "").await?.0,
        StatusCode::NOT_FOUND
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn deleting_oneself_or_the_last_admin_is_forbidden() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let me = contracts_ids::UserId::from_uuid(uuid::Uuid::parse_str(ADMIN)?);
    let own = send(
        &app,
        builder("DELETE", &format!("/api/identity/users/{me}"), &admin),
        "",
    )
    .await?;
    assert_eq!(own.0, StatusCode::FORBIDDEN);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn the_audit_log_is_read_newest_first_with_filters_and_needs_manage_users()
-> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let (reader, _) = signed_in(&app).await?;
    let denied = status_for(&app, get_with("/api/identity/audit", &reader)?).await?;
    assert_eq!(denied, StatusCode::FORBIDDEN);
    let path = format!("/api/identity/users/{}/status", reader_id());
    send(
        &app,
        builder("PUT", &path, &admin),
        r#"{"status":"suspended"}"#,
    )
    .await?;
    send(
        &app,
        builder("PUT", &path, &admin),
        r#"{"status":"active"}"#,
    )
    .await?;
    let all = get_json(&app, "/api/identity/audit?limit=2", &admin).await?;
    assert_eq!(at(&all, "/items/0/action"), "user_status_active");
    assert_eq!(at(&all, "/items/1/action"), "user_status_suspended");
    assert_ne!(at(&all, "/next"), "");
    let one = get_json(
        &app,
        "/api/identity/audit?action=user_status_suspended",
        &admin,
    )
    .await?;
    assert_eq!(item_count(&one), Some(1));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn audit_parameters_are_checked() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let admin = admin_cookie(&app, &pool).await?;
    let bad = get_json(&app, "/api/identity/audit?from=yesterday", &admin).await?;
    assert_eq!(at(&bad, "/error/details/fields/0"), "from");
    Ok(())
}

const IMAGE: &str = "/api/identity/me/profile-image";

fn png_bytes() -> Vec<u8> {
    [
        &[0x89, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a][..],
        b"pixels",
        &[b'I', b'E', b'N', b'D', 0xae, 0x42, 0x60, 0x82],
    ]
    .concat()
}

async fn put_image(app: &Router, cookie: &str, bytes: Vec<u8>) -> Result<Response<Body>, Failure> {
    let request = Request::put(IMAGE)
        .header(COOKIE, cookie)
        .body(Body::from(bytes))?;
    Ok(app.clone().oneshot(request).await?)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_profile_image_is_stored_validated_and_served_privately() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let (reader, _) = signed_in(&app).await?;
    let svg = put_image(&app, &reader, b"<svg/>".to_vec()).await?;
    assert_eq!(svg.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        put_image(&app, &reader, png_bytes()).await?.status(),
        StatusCode::NO_CONTENT
    );
    let me = get_json(&app, "/api/identity/me", &reader).await?;
    assert_eq!(me.pointer("/has_image"), Some(&Value::Bool(true)));
    let path = format!("/api/identity/users/{}/profile-image", reader_id());
    let own = app.clone().oneshot(get_with(&path, &reader)?).await?;
    assert_eq!(own.status(), StatusCode::OK);
    assert_eq!(header_text(&own, "cache-control"), "private, no-store");
    assert_eq!(header_text(&own, "content-type"), "image/png");
    let admin = admin_cookie(&app, &pool).await?;
    assert_eq!(
        status_for(&app, get_with(&path, &admin)?).await?,
        StatusCode::OK
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn another_reader_cannot_fetch_an_image_and_deleting_removes_it() -> Result<(), Failure> {
    let (app, pool) = app().await?;
    let (reader, _) = signed_in(&app).await?;
    put_image(&app, &reader, png_bytes()).await?;
    let admin_path = format!(
        "/api/identity/users/{}/profile-image",
        contracts_ids::UserId::from_uuid(uuid::Uuid::parse_str(ADMIN)?)
    );
    let _admin = admin_cookie(&app, &pool).await?;
    assert_eq!(
        status_for(&app, get_with(&admin_path, &reader)?).await?,
        StatusCode::FORBIDDEN
    );
    let delete = Request::delete(IMAGE)
        .header(COOKIE, &reader)
        .body(Body::empty())?;
    assert_eq!(status_for(&app, delete).await?, StatusCode::NO_CONTENT);
    let own = format!("/api/identity/users/{}/profile-image", reader_id());
    assert_eq!(
        status_for(&app, get_with(&own, &reader)?).await?,
        StatusCode::NOT_FOUND
    );
    let big = vec![0_u8; 2 * 1024 * 1024 + 10];
    assert_eq!(
        put_image(&app, &reader, big).await?.status(),
        StatusCode::PAYLOAD_TOO_LARGE
    );
    Ok(())
}

fn header_text<'a>(response: &'a Response<Body>, name: &str) -> &'a str {
    response
        .headers()
        .get(name)
        .and_then(|value| value.to_str().ok())
        .unwrap_or_default()
}
