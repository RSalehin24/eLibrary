//! The public session routes: sign-in, sign-out and the current session. The gateway checks
//! CSRF on mutations; these handlers only read and set the session cookie.

use std::sync::Arc;

use axum::extract::State;
use axum::http::HeaderMap;
use axum::response::Response;
use axum::routing::{get, post};
use axum::{Json, Router};
use domain_credentials::{Password, PasswordHash, SALT_BYTES};
use platform_config::{EnvSource, read_secret_file};
use platform_random::OsRandom;
use platform_time::{Clock, SystemClock};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;

use crate::cookie;
use crate::reply::{Failure, Reply};
use crate::session::{self, SessionState, csrf_token_for};
use crate::sign_in::{Client, Credentials, Services, SignInOutcome, sign_in};
use crate::sign_out::sign_out;
use crate::totp_verify::{TotpOutcome, Verifier, verify_totp};
use crate::users::{self, Profile};
use crate::vault::VaultKey;

type BuildError = Box<dyn std::error::Error + Send + Sync>;

struct Shared {
    pool: PgPool,
    dummy_hash: PasswordHash,
    key: VaultKey,
}

/// The routes with the vault key read from the secret file named by `ELIBRARY_TOTP_KEY_FILE`.
///
/// # Errors
/// The key file is missing or malformed, or the dummy hash could not be built.
pub fn routes(pool: PgPool) -> Result<Router, BuildError> {
    let text = read_secret_file(&EnvSource, "ELIBRARY_TOTP_KEY_FILE")?;
    routes_with_key(pool, VaultKey::from_hex(text.expose())?)
}

/// The routes under `/api/identity/auth`, ready to merge into the public router.
///
/// # Errors
/// The dummy password hash could not be built.
pub fn routes_with_key(pool: PgPool, key: VaultKey) -> Result<Router, BuildError> {
    // why: a fixed salt is fine; the dummy hash only equalises the cost of unknown accounts.
    let dummy_hash =
        PasswordHash::create(&Password::parse("dummy dummy dummy")?, &[7; SALT_BYTES])?;
    let shared = Arc::new(Shared {
        pool,
        dummy_hash,
        key,
    });
    Ok(Router::new()
        .route("/api/identity/auth/sign-in", post(sign_in_route))
        .route("/api/identity/auth/totp/verify", post(totp_verify_route))
        .route("/api/identity/auth/sign-out", post(sign_out_route))
        .route("/api/identity/auth/session", get(session_route))
        .with_state(shared))
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct SignInBody {
    email: String,
    password: String,
}

#[derive(Serialize)]
struct UserView {
    id: String,
    email: String,
    display_name: String,
    language: String,
    role: String,
}

impl From<Profile> for UserView {
    fn from(profile: Profile) -> Self {
        Self {
            id: contracts_ids::UserId::from_uuid(profile.id).to_string(),
            email: profile.email,
            display_name: profile.display_name,
            language: profile.language,
            role: profile.role,
        }
    }
}

#[derive(Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
enum SignInReply {
    Active { user: UserView, csrf_token: String },
    TotpRequired,
}

#[derive(Serialize)]
struct SessionReply {
    user: UserView,
    csrf_token: String,
    expires_at: i64,
}

async fn sign_in_route(
    State(shared): State<Arc<Shared>>,
    Json(body): Json<SignInBody>,
) -> Result<Response, Failure> {
    let services = Services {
        pool: &shared.pool,
        clock: &SystemClock,
        random: &OsRandom,
        dummy_hash: &shared.dummy_hash,
    };
    let credentials = Credentials {
        email: &body.email,
        password: &body.password,
    };
    match sign_in(&services, credentials, Client::default()).await? {
        SignInOutcome::SignedIn(issued) => {
            let profile = profile_of(&shared.pool, issued.user_id).await?;
            let reply = SignInReply::Active {
                user: profile.into(),
                csrf_token: issued.csrf_token.clone(),
            };
            Ok(Reply::with_session(&issued.token).json(&reply))
        }
        SignInOutcome::SecondFactorRequired(issued) => {
            Ok(Reply::with_session(&issued.token).json(&SignInReply::TotpRequired))
        }
        SignInOutcome::Rejected => Err(Failure::InvalidCredentials),
        SignInOutcome::Throttled => Err(Failure::RateLimited),
    }
}

async fn profile_of(pool: &PgPool, id: uuid::Uuid) -> Result<Profile, Failure> {
    users::find_profile(pool, id)
        .await?
        .ok_or(Failure::Unauthenticated)
}

async fn session_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
) -> Result<Json<SessionReply>, Failure> {
    let token = cookie::session_token(&headers).ok_or(Failure::Unauthenticated)?;
    let live = session::lookup(&shared.pool, token, SystemClock.now())
        .await?
        .ok_or(Failure::Unauthenticated)?;
    if live.state != SessionState::Authenticated {
        return Err(Failure::Unauthenticated);
    }
    let profile = profile_of(&shared.pool, live.user_id).await?;
    Ok(Json(SessionReply {
        user: profile.into(),
        csrf_token: csrf_token_for(token),
        expires_at: live.expires_at.unix_seconds(),
    }))
}

async fn sign_out_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
) -> Result<Response, Failure> {
    if let Some(token) = cookie::session_token(&headers) {
        sign_out(&shared.pool, token, SystemClock.now()).await?;
    }
    Ok(Reply::cleared_session().empty())
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct TotpBody {
    code: String,
}

async fn totp_verify_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Json(body): Json<TotpBody>,
) -> Result<Json<SignInReply>, Failure> {
    let token = cookie::session_token(&headers).ok_or(Failure::Unauthenticated)?;
    let now = SystemClock.now();
    let verifier = Verifier {
        pool: &shared.pool,
        key: &shared.key,
        now,
    };
    match verify_totp(verifier, token, &body.code).await? {
        TotpOutcome::Verified => active_reply(&shared.pool, token, now).await,
        TotpOutcome::Rejected => Err(Failure::InvalidCode),
        TotpOutcome::Throttled => Err(Failure::RateLimited),
    }
}

async fn active_reply(
    pool: &PgPool,
    token: &str,
    now: platform_time::Instant,
) -> Result<Json<SignInReply>, Failure> {
    let live = session::lookup(pool, token, now)
        .await?
        .ok_or(Failure::Unauthenticated)?;
    let profile = profile_of(pool, live.user_id).await?;
    Ok(Json(SignInReply::Active {
        user: profile.into(),
        csrf_token: csrf_token_for(token),
    }))
}
