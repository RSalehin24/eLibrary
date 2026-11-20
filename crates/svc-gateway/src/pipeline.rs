//! The request pipeline, in the fixed order of the design: route, request id, limits, identity,
//! forward, answer (README, "Request pipeline"). Every step is a small function; any failure
//! is a [`GatewayError`] and becomes the typed envelope.

use std::sync::{Arc, Mutex};
use std::time::Duration;

use axum::body::Body;
use axum::extract::State;
use axum::http::header::{AUTHORIZATION, CONTENT_LENGTH, COOKIE, HOST, ORIGIN};
use axum::http::request::Parts;
use axum::http::{HeaderMap, HeaderValue, Method, Request, Response};
use platform_random::OsRandom;
use platform_service_token::IssueRequest;
use platform_time::{Clock, Instant, SystemClock};

use crate::authorize::{IdentityLink, Question, Verdict, authorize};
use crate::config::GatewayConfig;
use crate::errors::GatewayError;
use crate::headers::{
    Identity, RequestId, apply_security_headers, stamp_identity, stamp_request_id, strip_untrusted,
};
use crate::limits::{
    ClientKey, ConcurrencyGate, RateLimiter, StreamRegistry, Verdict as Rate, gateway_policies,
};
use crate::routes::{RouteClass, Routed, Upstream, route};
use crate::upstream::{Fault, UpstreamClient};

const SESSION_COOKIE: &str = "__Host-session";
const CSRF_HEADER: &str = "x-csrf-token";
const TOKEN_LIFETIME: Duration = Duration::from_secs(30);
const JSON_BODY_LIMIT: u64 = 1024 * 1024;
const IMAGE_BODY_LIMIT: u64 = 2 * 1024 * 1024;
const READ_TIMEOUT: Duration = Duration::from_secs(5);
const WRITE_TIMEOUT: Duration = Duration::from_secs(15);
const EXPORT_TIMEOUT: Duration = Duration::from_secs(120);

/// Shared by every request.
pub struct Gateway {
    config: GatewayConfig,
    client: UpstreamClient,
    anonymous: Mutex<RateLimiter>,
    authentication: Mutex<RateLimiter>,
    subjects: Mutex<RateLimiter>,
    gate: ConcurrencyGate,
    /// Open-stream limits; used by the ingestion event stream (REQ-GWY-013).
    pub streams: StreamRegistry,
}

impl Gateway {
    #[must_use]
    pub fn new(config: GatewayConfig) -> Arc<Self> {
        let [anonymous, authentication, subjects] = gateway_policies();
        Arc::new(Self {
            config,
            client: UpstreamClient::default(),
            anonymous: Mutex::new(RateLimiter::new(anonymous)),
            authentication: Mutex::new(RateLimiter::new(authentication)),
            subjects: Mutex::new(RateLimiter::new(subjects)),
            gate: ConcurrencyGate::new(),
            streams: StreamRegistry::new(),
        })
    }
}

/// One request on its way through, without its body (a body is not `Sync`, so it travels
/// separately): what was asked, the request id and when it arrived.
struct Call {
    routed: Routed,
    parts: Parts,
    id: RequestId,
    now: Instant,
}

/// The axum handler for everything under the public listener.
pub async fn handle(State(gateway): State<Arc<Gateway>>, request: Request<Body>) -> Response<Body> {
    let (parts, body) = request.into_parts();
    let now = SystemClock.now();
    let id = RequestId::from_header(
        parts.headers.get("x-request-id"),
        now.unix_millis(),
        &OsRandom,
    );
    let mut response = match run(&gateway, (parts, body), (&id, now)).await {
        Ok(response) => response,
        Err(error) => error.respond(id.as_str()),
    };
    apply_security_headers(response.headers_mut());
    stamp_request_id(response.headers_mut(), &id);
    response
}

async fn run(
    gateway: &Gateway,
    request: (Parts, Body),
    arrival: (&RequestId, Instant),
) -> Result<Response<Body>, GatewayError> {
    let (parts, body) = request;
    let (id, now) = arrival;
    let routed = route(&parts.method, &parts.uri).ok_or(GatewayError::NotFound)?;
    let call = Call {
        routed,
        parts,
        id: id.clone(),
        now,
    };
    limit_address(gateway, &call)?;
    check_origin(gateway, &call.parts)?;
    check_size(&call.parts)?;
    let identity = identify(gateway, &call).await?;
    if let Some(who) = &identity {
        limit_subject(gateway, who, now)?;
    }
    forward(gateway, (call, body), identity).await
}

/// The caller's address prefix, from the proxy in front (the last `X-Forwarded-For` entry).
fn client_key(headers: &HeaderMap) -> ClientKey {
    let last = headers
        .get_all("x-forwarded-for")
        .iter()
        .filter_map(|value| value.to_str().ok())
        .flat_map(|line| line.split(','))
        .next_back()
        .map_or("unknown", str::trim);
    ClientKey::Address(address_prefix(last))
}

/// IPv4 to its /24, IPv6 to its first 64 bits; anything else as typed (bounded length).
fn address_prefix(address: &str) -> String {
    if address.contains(':') {
        return address.split(':').take(4).collect::<Vec<_>>().join(":");
    }
    let octets: Vec<&str> = address.split('.').collect();
    if octets.len() == 4 {
        return octets.into_iter().take(3).collect::<Vec<_>>().join(".");
    }
    address.chars().take(40).collect()
}

fn is_authentication(routed: &Routed) -> bool {
    routed.class == RouteClass::Public && routed.upstream == Upstream::Identity
}

fn rate(table: &Mutex<RateLimiter>, key: &ClientKey, now: Instant) -> Result<(), GatewayError> {
    let verdict = match table.lock() {
        Ok(mut limiter) => limiter.check(key, now),
        Err(poisoned) => poisoned.into_inner().check(key, now),
    };
    match verdict {
        Rate::Allowed => Ok(()),
        Rate::Limited {
            retry_after_seconds,
        } => Err(GatewayError::RateLimited {
            retry_after_seconds,
        }),
    }
}

fn limit_address(gateway: &Gateway, call: &Call) -> Result<(), GatewayError> {
    let key = client_key(&call.parts.headers);
    rate(&gateway.anonymous, &key, call.now)?;
    if is_authentication(&call.routed) {
        rate(&gateway.authentication, &key, call.now)?;
    }
    Ok(())
}

fn limit_subject(gateway: &Gateway, who: &Identity, now: Instant) -> Result<(), GatewayError> {
    rate(
        &gateway.subjects,
        &ClientKey::Subject(who.user_id.clone()),
        now,
    )
}

fn is_mutation(method: &Method) -> bool {
    !matches!(*method, Method::GET | Method::HEAD | Method::OPTIONS)
}

/// A mutation must come from this site: its `Origin` is the public origin (REQ-GWY-005).
fn check_origin(gateway: &Gateway, parts: &Parts) -> Result<(), GatewayError> {
    if !is_mutation(&parts.method) {
        return Ok(());
    }
    let expected = gateway.config.origin.url("");
    let sent = parts
        .headers
        .get(ORIGIN)
        .and_then(|value| value.to_str().ok());
    (sent == Some(expected.as_str()))
        .then_some(())
        .ok_or(GatewayError::CsrfInvalid)
}

fn body_limit(parts: &Parts) -> u64 {
    if parts.uri.path().ends_with("/me/profile-image") {
        IMAGE_BODY_LIMIT
    } else {
        JSON_BODY_LIMIT
    }
}

/// Refuses a declared body above the route's limit before anything is forwarded.
fn check_size(parts: &Parts) -> Result<(), GatewayError> {
    let declared = parts
        .headers
        .get(CONTENT_LENGTH)
        .and_then(|value| value.to_str().ok())
        .and_then(|text| text.parse::<u64>().ok());
    match declared {
        Some(size) if size > body_limit(parts) => Err(GatewayError::BodyTooLarge),
        Some(_) | None => Ok(()),
    }
}

fn timeout_for(parts: &Parts) -> Duration {
    if parts.uri.path().ends_with("/export") {
        EXPORT_TIMEOUT
    } else if is_mutation(&parts.method) {
        WRITE_TIMEOUT
    } else {
        READ_TIMEOUT
    }
}

fn session_cookie(headers: &HeaderMap) -> Option<&str> {
    headers
        .get_all(COOKIE)
        .iter()
        .filter_map(|value| value.to_str().ok())
        .flat_map(|line| line.split(';'))
        .filter_map(|pair| pair.trim().split_once('='))
        .find(|(name, _)| *name == SESSION_COOKIE)
        .map(|(_, value)| value)
}

fn service_token(
    gateway: &Gateway,
    callee: Upstream,
    now: Instant,
) -> Result<String, GatewayError> {
    let name = platform_service_token::ServiceName::parse(callee.name())
        .map_err(|_| GatewayError::UpstreamFailed)?;
    let request = IssueRequest {
        callee: &name,
        now,
        lifetime: TOKEN_LIFETIME,
    };
    gateway
        .config
        .issuer
        .issue(request)
        .map(|token| token.as_str().to_owned())
        .ok_or(GatewayError::UpstreamFailed)
}

fn question_of(parts: &Parts) -> Question<'_> {
    let text = |name: &str| {
        parts
            .headers
            .get(name)
            .and_then(|value| value.to_str().ok())
    };
    Question {
        method: parts.method.as_str(),
        path: parts.uri.path(),
        cookie: session_cookie(&parts.headers),
        origin: text("origin"),
        csrf_token: text(CSRF_HEADER),
    }
}

/// Turns identity's verdict into the identity to forward or the error to answer.
fn decide(verdict: Verdict) -> Result<Identity, GatewayError> {
    match verdict {
        Verdict::Allow(identity) => Ok(identity),
        Verdict::Unauthenticated => Err(GatewayError::Unauthenticated),
        Verdict::Denied(reason) if reason == "csrf_invalid" => Err(GatewayError::CsrfInvalid),
        Verdict::Denied(reason) => Err(GatewayError::Denied(reason)),
        Verdict::Unavailable => Err(GatewayError::IdentityUnavailable),
    }
}

/// Asks identity about a protected request; `None` for a public route.
async fn identify(gateway: &Gateway, call: &Call) -> Result<Option<Identity>, GatewayError> {
    if call.routed.class == RouteClass::Public {
        return Ok(None);
    }
    let link = IdentityLink {
        base: gateway.config.base(Upstream::Identity).to_owned(),
        service_token: service_token(gateway, Upstream::Identity, call.now)
            .map_err(|_| GatewayError::IdentityUnavailable)?,
    };
    let question = question_of(&call.parts);
    decide(authorize(&gateway.client, &link, &question).await).map(Some)
}

/// The headers for the upstream: untrusted ones stripped, identity stamped from the verdict, the
/// session cookie kept only for identity (which owns sessions).
fn upstream_headers(call: &Call, identity: Option<&Identity>) -> HeaderMap {
    let mut headers = call.parts.headers.clone();
    let cookie = headers.get(COOKIE).cloned();
    strip_untrusted(&mut headers);
    headers.remove(HOST);
    headers.remove(COOKIE);
    headers.remove(CSRF_HEADER);
    if call.routed.upstream == Upstream::Identity {
        headers.extend(cookie.map(|value| (COOKIE, value)));
    }
    if let Some(who) = identity {
        stamp_identity(&mut headers, who);
    }
    stamp_request_id(&mut headers, &call.id);
    headers
}

fn upstream_request(
    gateway: &Gateway,
    request: (Call, Body),
    identity: Option<&Identity>,
) -> Result<Request<Body>, GatewayError> {
    let (call, body) = request;
    let mut headers = upstream_headers(&call, identity);
    let token = service_token(gateway, call.routed.upstream, call.now)?;
    let value = HeaderValue::from_str(&format!("Service {token}"))
        .map_err(|_| GatewayError::UpstreamFailed)?;
    headers.insert(AUTHORIZATION, value);
    let base = gateway.config.base(call.routed.upstream);
    let mut request = Request::builder()
        .method(call.parts.method)
        .uri(format!("{base}{}", call.routed.path_and_query))
        .body(body)
        .map_err(|_| GatewayError::UpstreamFailed)?;
    *request.headers_mut() = headers;
    Ok(request)
}

async fn forward(
    gateway: &Gateway,
    request: (Call, Body),
    identity: Option<Identity>,
) -> Result<Response<Body>, GatewayError> {
    let call = &request.0;
    let timeout = timeout_for(&call.parts);
    let _permit = gateway
        .gate
        .try_acquire(call.routed.upstream.name())
        .ok_or(GatewayError::Overloaded)?;
    let request = upstream_request(gateway, request, identity.as_ref())?;
    let mut response =
        gateway
            .client
            .send(request, timeout)
            .await
            .map_err(|fault| match fault {
                Fault::Timeout => GatewayError::UpstreamTimeout,
                Fault::Unreachable => GatewayError::UpstreamFailed,
            })?;
    strip_untrusted(response.headers_mut());
    Ok(response)
}
