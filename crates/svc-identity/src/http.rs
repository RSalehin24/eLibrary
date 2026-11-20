//! The public session routes: sign-in, sign-out and the current session. The gateway checks
//! CSRF on mutations; these handlers only read and set the session cookie.

use std::sync::Arc;

use axum::extract::{FromRequestParts, Path, RawQuery, State};
use axum::http::request::Parts;
use axum::http::{HeaderMap, StatusCode};
use axum::response::Response;
use axum::routing::{get, post, put};
use axum::{Json, Router};
use domain_credentials::{Password, PasswordHash, SALT_BYTES};
use platform_config::{EnvSource, PublicOrigin, read_peer_keys, read_secret_file};
use platform_random::OsRandom;
use platform_service_token::{
    KeyId, KeyOwner, KeyRing, ServiceName, SigningKey, Verifier as ServiceVerifier,
};
use platform_time::{Clock, SystemClock};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;

use crate::admin_change::{
    self, Change as AccountChange, ROLES, Request as AdminRequest, SETTABLE_STATUSES,
};
use crate::admin_users::{self, UserDetail, UserPage};
use crate::audit_read::{self, AuditPage};
use crate::capabilities::{self, Capabilities};
use crate::cookie;
use crate::credential_links::{self, Context as LinkContext, Redeemed};
use crate::export::{self, Export};
use crate::invite::{self, Invited, Inviter, Person};
use crate::kindle::{self, Addresses, Refusal, Replacement};
use crate::me::{self, Change, Edited, Me};
use crate::password_change::{Change as PasswordChange, change_password};
use crate::profile_image;
use crate::query;
use crate::reply::{Failure, Reply};
use crate::session::{self, SessionState, csrf_token_for};
use crate::sign_in::{Client, Credentials, Services, SignInOutcome, sign_in};
use crate::sign_out::sign_out;
use crate::totp_manage::{self, Enrolment, Manage, Reauth, Revealed};
use crate::totp_verify::{TotpOutcome, Verifier, verify_totp};
use crate::users::{self, Profile};
use crate::vault::VaultKey;

type BuildError = Box<dyn std::error::Error + Send + Sync>;

mod grant_routes;
mod internal_routes;

struct Shared {
    pool: PgPool,
    dummy_hash: PasswordHash,
    key: VaultKey,
    verifier: ServiceVerifier,
    origin: PublicOrigin,
}

/// What the routes need besides the database: the TOTP vault key, the verifier of internal
/// service tokens and the public origin of emailed links.
pub struct Settings {
    pub key: VaultKey,
    pub verifier: ServiceVerifier,
    pub origin: PublicOrigin,
}

/// The routes with their settings read from the process environment: the vault key file named
/// by `ELIBRARY_TOTP_KEY_FILE`, `ELIBRARY_PUBLIC_ORIGIN` (D-100) and the peer token keys
/// `ELIBRARY_SERVICE_CALLERS` (D-101).
///
/// # Errors
/// A missing or malformed setting or key file, or the dummy hash could not be built.
pub fn routes(pool: PgPool) -> Result<Router, BuildError> {
    let text = read_secret_file(&EnvSource, "ELIBRARY_TOTP_KEY_FILE")?;
    let settings = Settings {
        key: VaultKey::from_hex(text.expose())?,
        verifier: peer_verifier(&EnvSource)?,
        origin: PublicOrigin::load(&EnvSource)?,
    };
    routes_with(pool, settings)
}

/// The verifier of `identity`'s callers, from the configured peer keys.
fn peer_verifier(
    source: &impl platform_config::ConfigSource,
) -> Result<ServiceVerifier, BuildError> {
    let mut ring = KeyRing::default();
    for peer in read_peer_keys(source)? {
        let owner = KeyOwner {
            service: ServiceName::parse(&peer.service)?,
            id: KeyId(peer.key_id),
        };
        ring = ring.with(owner, SigningKey::from_hex(peer.secret.expose())?);
    }
    Ok(ServiceVerifier::new(ServiceName::parse("identity")?, ring))
}

/// The routes under `/api/identity` and `/internal`, ready to merge into the public router.
///
/// # Errors
/// The dummy password hash could not be built.
pub fn routes_with(pool: PgPool, settings: Settings) -> Result<Router, BuildError> {
    // why: a fixed salt is fine; the dummy hash only equalises the cost of unknown accounts.
    let dummy_hash =
        PasswordHash::create(&Password::parse("dummy dummy dummy")?, &[7; SALT_BYTES])?;
    let shared = Arc::new(Shared {
        pool,
        dummy_hash,
        key: settings.key,
        verifier: settings.verifier,
        origin: settings.origin,
    });
    Ok(Router::new()
        .merge(grant_routes::routes())
        .merge(internal_routes::routes())
        .merge(admin_routes())
        .merge(account_routes())
        .with_state(shared))
}

/// The user administration routes (`manage_users`).
fn admin_routes() -> Router<Arc<Shared>> {
    Router::new()
        .route(
            "/api/identity/users",
            get(users_list_route).post(user_invite_route),
        )
        .route(
            "/api/identity/users/{id}/resend-invite",
            post(resend_invite_route),
        )
        .route(
            "/api/identity/users/{id}",
            get(users_detail_route)
                .patch(user_edit_route)
                .delete(user_delete_route),
        )
        .route(
            "/api/identity/users/{id}/read-once/{book_id}/reset",
            post(read_once_reset_route),
        )
        .route("/api/identity/audit", get(audit_route))
        .route("/api/identity/users/{id}/status", put(user_status_route))
        .route("/api/identity/users/{id}/role", put(user_role_route))
}

/// Sign-in, links, session and the signed-in user's own account.
fn account_routes() -> Router<Arc<Shared>> {
    session_routes().merge(me_routes())
}

fn session_routes() -> Router<Arc<Shared>> {
    Router::new()
        .route("/api/identity/invites/accept", post(accept_invite_route))
        .route(
            "/api/identity/password-reset/request",
            post(reset_request_route),
        )
        .route(
            "/api/identity/password-reset/confirm",
            post(reset_confirm_route),
        )
        .route("/api/identity/auth/sign-in", post(sign_in_route))
        .route("/api/identity/auth/totp/verify", post(totp_verify_route))
        .route("/api/identity/auth/sign-out", post(sign_out_route))
        .route("/api/identity/auth/session", get(session_route))
}

/// The signed-in user's own account.
fn me_routes() -> Router<Arc<Shared>> {
    Router::new()
        .route("/api/identity/me/capabilities", get(capabilities_route))
        .route(
            "/api/identity/me/kindle-addresses",
            get(kindle_list_route).put(kindle_replace_route),
        )
        .route(
            "/api/identity/me/profile-image",
            axum::routing::put(image_put_route).delete(image_delete_route),
        )
        .route(
            "/api/identity/users/{id}/profile-image",
            get(image_get_route),
        )
        .route("/api/identity/me/export", get(export_route))
        .route("/api/identity/me/password", post(password_route))
        .route("/api/identity/me/totp", get(totp_status_route))
        .route("/api/identity/me/totp/setup", post(totp_setup_route))
        .route("/api/identity/me/totp/confirm", post(totp_confirm_route))
        .route("/api/identity/me/totp/disable", post(totp_disable_route))
        .route("/api/identity/me/totp/reveal", post(totp_reveal_route))
        .route("/api/identity/me", get(me_route).patch(me_update_route))
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

/// A fully signed-in session; pending-TOTP and unknown sessions are not signed in.
async fn signed_in_session(
    shared: &Shared,
    headers: &HeaderMap,
) -> Result<session::LiveSession, Failure> {
    let token = cookie::session_token(headers).ok_or(Failure::Unauthenticated)?;
    let live = session::lookup(&shared.pool, token, SystemClock.now())
        .await?
        .ok_or(Failure::Unauthenticated)?;
    if live.state == SessionState::Authenticated {
        Ok(live)
    } else {
        Err(Failure::Unauthenticated)
    }
}

async fn signed_in_user(shared: &Shared, headers: &HeaderMap) -> Result<uuid::Uuid, Failure> {
    Ok(signed_in_session(shared, headers).await?.user_id)
}

async fn me_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
) -> Result<Json<Me>, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    let me = me::find(&shared.pool, id)
        .await?
        .ok_or(Failure::Unauthenticated)?;
    Ok(Json(me))
}

async fn me_update_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Json(body): Json<Change>,
) -> Result<Json<Me>, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    let edit = me::validate(body, id, SystemClock.now()).map_err(Failure::Invalid)?;
    if !me::update(&shared.pool, edit).await? {
        return Err(Failure::Unauthenticated);
    }
    me_route(State(shared), headers).await
}

async fn capabilities_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
) -> Result<Json<Capabilities>, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    let set = capabilities::resolve(&shared.pool, id, SystemClock.now())
        .await?
        .ok_or(Failure::Unauthenticated)?;
    Ok(Json(set))
}

#[derive(Serialize)]
struct TotpStatus {
    state: &'static str,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ReauthBody {
    password: String,
    code: String,
}

impl Shared {
    fn manage(&self) -> Manage<'_> {
        Manage {
            pool: &self.pool,
            key: &self.key,
            now: SystemClock.now(),
        }
    }
}

fn reauth(user: uuid::Uuid, body: &ReauthBody) -> Reauth<'_> {
    Reauth {
        user,
        password: &body.password,
        code: &body.code,
    }
}

async fn totp_status_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
) -> Result<Json<TotpStatus>, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    let state = totp_manage::status(&shared.pool, id).await?;
    Ok(Json(TotpStatus { state }))
}

async fn totp_setup_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
) -> Result<Json<Enrolment>, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    let enrolment = totp_manage::setup(shared.manage(), id).await?.settle()?;
    Ok(Json(enrolment))
}

async fn totp_confirm_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Json(body): Json<TotpBody>,
) -> Result<Json<TotpStatus>, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    totp_manage::confirm(shared.manage(), id, &body.code)
        .await?
        .settle()?;
    Ok(Json(TotpStatus { state: "on" }))
}

async fn totp_disable_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Json(body): Json<ReauthBody>,
) -> Result<Response, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    totp_manage::disable(shared.manage(), reauth(id, &body))
        .await?
        .settle()?;
    Ok(Reply::none().empty())
}

async fn totp_reveal_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Json(body): Json<ReauthBody>,
) -> Result<Json<Revealed>, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    let revealed = totp_manage::reveal(shared.manage(), reauth(id, &body))
        .await?
        .settle()?;
    Ok(Json(revealed))
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PasswordBody {
    current_password: String,
    new_password: String,
    code: Option<String>,
}

async fn password_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Json(body): Json<PasswordBody>,
) -> Result<Response, Failure> {
    let session = signed_in_session(&shared, &headers).await?;
    let change = PasswordChange {
        session: &session,
        current: &body.current_password,
        new: &body.new_password,
        code: body.code.as_deref(),
    };
    change_password(shared.manage(), change).await?.settle()?;
    Ok(Reply::none().empty())
}

/// The user, if the account holds the `kindle` scope.
async fn kindle_user(shared: &Shared, headers: &HeaderMap) -> Result<uuid::Uuid, Failure> {
    let id = signed_in_user(shared, headers).await?;
    let set = capabilities::resolve(&shared.pool, id, SystemClock.now())
        .await?
        .ok_or(Failure::Unauthenticated)?;
    if set.allows(contracts_http::Scope::Kindle) {
        Ok(id)
    } else {
        Err(Failure::Refused(contracts_http::CommonErrorCode::Forbidden))
    }
}

async fn kindle_list_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
) -> Result<Json<Addresses>, Failure> {
    let id = kindle_user(&shared, &headers).await?;
    Ok(Json(kindle::list(&shared.pool, id).await?))
}

async fn kindle_replace_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Json(body): Json<Replacement>,
) -> Result<Json<Addresses>, Failure> {
    let id = kindle_user(&shared, &headers).await?;
    let parsed = kindle::validate(&body).map_err(|refusal| match refusal {
        Refusal::TooMany => Failure::Refused(contracts_http::CommonErrorCode::LimitExceeded),
        Refusal::Invalid => Failure::Invalid("addresses"),
    })?;
    kindle::replace(&shared.pool, id, &parsed).await?;
    Ok(Json(kindle::list(&shared.pool, id).await?))
}

async fn export_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
) -> Result<Json<Export>, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    let export = export::collect(&shared.pool, id)
        .await?
        .ok_or(Failure::Unauthenticated)?;
    Ok(Json(export))
}

/// The caller, if their session is complete and the account holds `manage_users`.
async fn administrator(shared: &Shared, headers: &HeaderMap) -> Result<uuid::Uuid, Failure> {
    let id = signed_in_user(shared, headers).await?;
    let set = capabilities::resolve(&shared.pool, id, SystemClock.now())
        .await?
        .ok_or(Failure::Unauthenticated)?;
    if set.allows(contracts_http::Scope::ManageUsers) {
        Ok(id)
    } else {
        Err(Failure::Refused(contracts_http::CommonErrorCode::Forbidden))
    }
}

async fn users_list_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    RawQuery(query): RawQuery,
) -> Result<Json<UserPage>, Failure> {
    administrator(&shared, &headers).await?;
    let request =
        admin_users::listing(&query::parse(query.as_deref())).map_err(Failure::Invalid)?;
    Ok(Json(admin_users::list(&shared.pool, request).await?))
}

async fn users_detail_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Path(id): Path<String>,
) -> Result<Json<UserDetail>, Failure> {
    administrator(&shared, &headers).await?;
    let missing = || Failure::Refused(contracts_http::CommonErrorCode::NotFound);
    let key = id.parse::<contracts_ids::UserId>().map_err(|_| missing())?;
    let detail = admin_users::detail(&shared.pool, key.as_uuid()).await?;
    detail.map(Json).ok_or_else(missing)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct StatusBody {
    status: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RoleBody {
    role: String,
}

fn user_key(id: &str) -> Result<uuid::Uuid, Failure> {
    id.parse::<contracts_ids::UserId>()
        .map(|key| key.as_uuid())
        .map_err(|_| Failure::Refused(contracts_http::CommonErrorCode::NotFound))
}

fn settled(change: AccountChange) -> Result<(), Failure> {
    match change {
        AccountChange::Done => Ok(()),
        AccountChange::Refused(code) => Err(Failure::Refused(code)),
    }
}

async fn user_status_route(
    State(shared): State<Arc<Shared>>,
    admin: AdminOnUser,
    Json(body): Json<StatusBody>,
) -> Result<Json<UserDetail>, Failure> {
    let AdminOnUser { actor, target, .. } = admin;
    if !SETTABLE_STATUSES.contains(&body.status.as_str()) {
        return Err(Failure::Invalid("status"));
    }
    let request = AdminRequest {
        pool: &shared.pool,
        now: SystemClock.now(),
        actor,
        target,
    };
    settled(admin_change::set_status(request, &body.status).await?)?;
    updated_detail(&shared, target).await
}

async fn user_role_route(
    State(shared): State<Arc<Shared>>,
    admin: AdminOnUser,
    Json(body): Json<RoleBody>,
) -> Result<Json<UserDetail>, Failure> {
    let AdminOnUser { actor, target, .. } = admin;
    if !ROLES.contains(&body.role.as_str()) {
        return Err(Failure::Invalid("role"));
    }
    let request = AdminRequest {
        pool: &shared.pool,
        now: SystemClock.now(),
        actor,
        target,
    };
    settled(admin_change::set_role(request, &body.role).await?)?;
    updated_detail(&shared, target).await
}

async fn updated_detail(shared: &Shared, id: uuid::Uuid) -> Result<Json<UserDetail>, Failure> {
    let detail = admin_users::detail(&shared.pool, id).await?;
    detail
        .map(Json)
        .ok_or(Failure::Refused(contracts_http::CommonErrorCode::NotFound))
}

/// The revision in `If-Match` (`3` or `"3"`).
fn if_match(headers: &HeaderMap) -> Option<i64> {
    let value = headers.get(axum::http::header::IF_MATCH)?.to_str().ok()?;
    value.trim().trim_matches('"').parse().ok()
}

/// An administrator and the user a `/users/{id}/...` route is about, checked before the body is
/// read. `rest` holds any further path parameters and `revision` the `If-Match` value.
struct AdminOnUser {
    actor: uuid::Uuid,
    target: uuid::Uuid,
    rest: Vec<String>,
    revision: Option<i64>,
}

impl FromRequestParts<Arc<Shared>> for AdminOnUser {
    type Rejection = Failure;

    async fn from_request_parts(parts: &mut Parts, shared: &Arc<Shared>) -> Result<Self, Failure> {
        let actor = administrator(shared, &parts.headers).await?;
        let Path(mut params) = Path::<Vec<String>>::from_request_parts(parts, shared)
            .await
            .map_err(|_| Failure::Refused(contracts_http::CommonErrorCode::NotFound))?;
        let first = (!params.is_empty()).then(|| params.remove(0));
        let target = user_key(first.as_deref().unwrap_or_default())?;
        Ok(Self {
            actor,
            target,
            rest: params,
            revision: if_match(&parts.headers),
        })
    }
}

async fn user_edit_route(
    State(shared): State<Arc<Shared>>,
    admin: AdminOnUser,
    Json(body): Json<Change>,
) -> Result<Json<UserDetail>, Failure> {
    let revision = admin.revision.ok_or(Failure::Invalid("if_match"))?;
    let edit = me::validate(body, admin.target, SystemClock.now()).map_err(Failure::Invalid)?;
    match me::update_at_revision(&shared.pool, edit, revision).await? {
        Edited::Done => updated_detail(&shared, admin.target).await,
        Edited::NotFound => Err(Failure::Refused(contracts_http::CommonErrorCode::NotFound)),
        Edited::Stale => Err(Failure::Refused(
            contracts_http::CommonErrorCode::StaleRevision,
        )),
    }
}

async fn read_once_reset_route(
    State(shared): State<Arc<Shared>>,
    admin: AdminOnUser,
) -> Result<StatusCode, Failure> {
    let book = admin
        .rest
        .first()
        .and_then(|text| text.parse::<contracts_ids::BookId>().ok())
        .ok_or(Failure::Refused(contracts_http::CommonErrorCode::NotFound))?;
    let request = AdminRequest {
        pool: &shared.pool,
        now: SystemClock.now(),
        actor: admin.actor,
        target: admin.target,
    };
    settled(admin_change::reset_read_once(request, book.as_uuid()).await?)?;
    Ok(StatusCode::NO_CONTENT)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct InviteBody {
    email: String,
    display_name: String,
    role: String,
    language: String,
}

/// The invitation fields, or the name of the first wrong one.
fn person(body: &InviteBody) -> Result<Person<'_>, &'static str> {
    let email = domain_credentials::Email::parse(&body.email).map_err(|_| "email")?;
    let display_name = me::valid_name(&body.display_name).ok_or("display_name")?;
    let role = ROLES
        .iter()
        .find(|role| **role == body.role)
        .ok_or("role")?;
    let language = ["bn", "en"]
        .iter()
        .find(|code| **code == body.language)
        .ok_or("language")?;
    Ok(Person {
        email,
        display_name,
        role,
        language,
    })
}

fn inviter(shared: &Shared, actor: uuid::Uuid, target: uuid::Uuid) -> Inviter<'_> {
    Inviter {
        pool: &shared.pool,
        key: &shared.key,
        request: AdminRequest {
            pool: &shared.pool,
            now: SystemClock.now(),
            actor,
            target,
        },
    }
}

fn invited(result: Invited) -> Result<uuid::Uuid, Failure> {
    match result {
        Invited::Done(id) => Ok(id),
        Invited::EmailTaken => Err(Failure::Named(crate::reply::Named::EmailTaken)),
        Invited::Refused(code) => Err(Failure::Refused(code)),
    }
}

async fn user_invite_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    Json(body): Json<InviteBody>,
) -> Result<(StatusCode, Json<UserDetail>), Failure> {
    let actor = administrator(&shared, &headers).await?;
    let person = person(&body).map_err(Failure::Invalid)?;
    let id = invited(invite::invite(inviter(&shared, actor, uuid::Uuid::nil()), person).await?)?;
    let detail = updated_detail(&shared, id).await?;
    Ok((StatusCode::CREATED, detail))
}

async fn resend_invite_route(
    State(shared): State<Arc<Shared>>,
    admin: AdminOnUser,
) -> Result<StatusCode, Failure> {
    invited(invite::resend(inviter(&shared, admin.actor, admin.target)).await?)?;
    Ok(StatusCode::NO_CONTENT)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct LinkBody {
    token: String,
    password: String,
}

#[derive(Serialize)]
struct Activated {
    status: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    next_step: Option<&'static str>,
}

fn link_context(shared: &Shared) -> LinkContext<'_> {
    LinkContext {
        pool: &shared.pool,
        key: &shared.key,
        now: SystemClock.now(),
    }
}

fn redeemed(result: Redeemed, next_step: &'static str) -> Result<Json<Activated>, Failure> {
    match result {
        Redeemed::Done { totp_required } => Ok(Json(Activated {
            status: "active",
            next_step: totp_required.then_some(next_step),
        })),
        Redeemed::LinkInvalid => Err(Failure::Named(crate::reply::Named::LinkInvalid)),
        Redeemed::WeakPassword => Err(Failure::WeakPassword),
    }
}

async fn accept_invite_route(
    State(shared): State<Arc<Shared>>,
    Json(body): Json<LinkBody>,
) -> Result<Json<Activated>, Failure> {
    let result =
        credential_links::accept_invite(link_context(&shared), &body.token, &body.password).await?;
    redeemed(result, "totp_setup")
}

async fn reset_confirm_route(
    State(shared): State<Arc<Shared>>,
    Json(body): Json<LinkBody>,
) -> Result<Json<Activated>, Failure> {
    let result =
        credential_links::confirm_reset(link_context(&shared), &body.token, &body.password).await?;
    redeemed(result, "totp_setup")
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ResetRequestBody {
    email: String,
}

async fn reset_request_route(
    State(shared): State<Arc<Shared>>,
    Json(body): Json<ResetRequestBody>,
) -> Result<StatusCode, Failure> {
    let within_limit = credential_links::request_reset(link_context(&shared), &body.email).await?;
    if within_limit {
        Ok(StatusCode::ACCEPTED)
    } else {
        Err(Failure::RateLimited)
    }
}

async fn audit_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    RawQuery(raw): RawQuery,
) -> Result<Json<AuditPage>, Failure> {
    administrator(&shared, &headers).await?;
    let request = audit_read::query(&query::parse(raw.as_deref())).map_err(Failure::Invalid)?;
    Ok(Json(audit_read::read(&shared.pool, request).await?))
}

async fn user_delete_route(
    State(shared): State<Arc<Shared>>,
    admin: AdminOnUser,
) -> Result<StatusCode, Failure> {
    let request = AdminRequest {
        pool: &shared.pool,
        now: SystemClock.now(),
        actor: admin.actor,
        target: admin.target,
    };
    settled(admin_change::delete_user(request).await?)?;
    Ok(StatusCode::NO_CONTENT)
}

async fn image_put_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
    body: axum::body::Body,
) -> Result<StatusCode, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    let bytes = axum::body::to_bytes(body, profile_image::MAX_BYTES + 1)
        .await
        .map_err(|_| Failure::Refused(contracts_http::CommonErrorCode::BodyTooLarge))?;
    let kind =
        profile_image::sniff(&bytes).ok_or(Failure::Named(crate::reply::Named::InvalidImage))?;
    profile_image::save(&shared.pool, (id, SystemClock.now()), (kind, &bytes)).await?;
    Ok(StatusCode::NO_CONTENT)
}

async fn image_delete_route(
    State(shared): State<Arc<Shared>>,
    headers: HeaderMap,
) -> Result<StatusCode, Failure> {
    let id = signed_in_user(&shared, &headers).await?;
    profile_image::remove(&shared.pool, id).await?;
    Ok(StatusCode::NO_CONTENT)
}

async fn image_get_route(
    State(shared): State<Arc<Shared>>,
    admin: AdminOnImage,
) -> Result<Response, Failure> {
    let stored = profile_image::load(&shared.pool, admin.owner)
        .await?
        .ok_or(Failure::Refused(contracts_http::CommonErrorCode::NotFound))?;
    Response::builder()
        .header(axum::http::header::CONTENT_TYPE, stored.content_type)
        .header(axum::http::header::CACHE_CONTROL, "private, no-store")
        .header("X-Content-Type-Options", "nosniff")
        .body(axum::body::Body::from(stored.bytes))
        .map_err(|_| Failure::Internal)
}

/// The caller and the user whose image is asked for, allowed only for that user or for a
/// holder of `manage_users` (REQ-IDN-034).
struct AdminOnImage {
    owner: uuid::Uuid,
}

impl FromRequestParts<Arc<Shared>> for AdminOnImage {
    type Rejection = Failure;

    async fn from_request_parts(parts: &mut Parts, shared: &Arc<Shared>) -> Result<Self, Failure> {
        let caller = signed_in_user(shared, &parts.headers).await?;
        let Path(id) = Path::<String>::from_request_parts(parts, shared)
            .await
            .map_err(|_| Failure::Refused(contracts_http::CommonErrorCode::NotFound))?;
        let owner = user_key(&id)?;
        let allowed = caller == owner || administrator(shared, &parts.headers).await.is_ok();
        allowed
            .then_some(Self { owner })
            .ok_or(Failure::Refused(contracts_http::CommonErrorCode::Forbidden))
    }
}
