//! The pipeline end to end against stub upstreams on real sockets (TST-GWY-001, 002, 005, 007,
//! 010, 012, 016). No database or other service is needed.

use std::sync::{Arc, Mutex};

use axum::Router;
use axum::body::Body;
use axum::extract::State;
use axum::http::{HeaderMap, Method, Request, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::any;
use platform_config::MapSource;
use serde_json::Value;
use svc_gateway::config::GatewayConfig;
use svc_gateway::pipeline::{Gateway, handle};
use tower::ServiceExt;

type Failure = Box<dyn std::error::Error>;

const ORIGIN: &str = "https://library.test";

/// What a stub saw: method, path and headers.
#[derive(Clone)]
struct Seen {
    method: Method,
    path: String,
    headers: HeaderMap,
}

#[derive(Clone)]
struct Stub {
    seen: Arc<Mutex<Vec<Seen>>>,
    answer: Arc<dyn Fn(&str) -> Response + Send + Sync>,
}

async fn stub_handler(State(stub): State<Stub>, request: Request<Body>) -> Response {
    let path = request.uri().path().to_owned();
    if let Ok(mut seen) = stub.seen.lock() {
        seen.push(Seen {
            method: request.method().clone(),
            path: path.clone(),
            headers: request.headers().clone(),
        });
    }
    (stub.answer)(&path)
}

/// Starts a stub service; returns its base URL and the list of requests it saw.
async fn start(
    answer: impl Fn(&str) -> Response + Send + Sync + 'static,
) -> Result<(String, Arc<Mutex<Vec<Seen>>>), Failure> {
    let seen = Arc::new(Mutex::new(Vec::new()));
    let stub = Stub {
        seen: Arc::clone(&seen),
        answer: Arc::new(answer),
    };
    let app = Router::new().fallback(any(stub_handler)).with_state(stub);
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await?;
    let base = format!("http://{}", listener.local_addr()?);
    tokio::spawn(async move { axum::serve(listener, app).await });
    Ok((base, seen))
}

fn json_response(status: StatusCode, body: &str) -> Response {
    (
        status,
        [("content-type", "application/json")],
        body.to_owned(),
    )
        .into_response()
}

fn allow(_path: &str) -> Response {
    json_response(
        StatusCode::OK,
        r#"{"user_id":"u-1","scopes":["browse","read"],"grant_version":4}"#,
    )
}

/// The signing key file, written once so parallel tests never read it half-written.
fn key_file() -> Result<String, Failure> {
    static PATH: std::sync::OnceLock<Result<String, String>> = std::sync::OnceLock::new();
    let written = PATH.get_or_init(|| {
        let path = format!("{}/gateway-test-key", env!("CARGO_TARGET_TMPDIR"));
        std::fs::write(&path, "ab".repeat(32))
            .map(|()| path)
            .map_err(|error| error.to_string())
    });
    written.clone().map_err(Into::into)
}

fn app(identity: &str, catalog: &str) -> Result<Router, Failure> {
    let source = MapSource::default()
        .with("ELIBRARY_UPSTREAM_IDENTITY", identity)
        .with("ELIBRARY_UPSTREAM_CATALOG", catalog)
        .with("ELIBRARY_UPSTREAM_READER", "http://127.0.0.1:1")
        .with("ELIBRARY_UPSTREAM_INGESTION", "http://127.0.0.1:1")
        .with("ELIBRARY_PUBLIC_ORIGIN", ORIGIN)
        .with("ELIBRARY_SERVICE_TOKEN_KEY_FILE", &key_file()?);
    let config = GatewayConfig::load(&source).map_err(|error| error.to_string())?;
    Ok(Router::new()
        .fallback(handle)
        .with_state(Gateway::new(config)))
}

fn request(method: &str, path: &str) -> axum::http::request::Builder {
    Request::builder().method(method).uri(path)
}

async fn send(app: &Router, builder: axum::http::request::Builder) -> Result<Response, Failure> {
    Ok(app.clone().oneshot(builder.body(Body::empty())?).await?)
}

async fn error_code(response: Response) -> Result<String, Failure> {
    let bytes = axum::body::to_bytes(response.into_body(), 64 * 1024).await?;
    let value: Value = serde_json::from_slice(&bytes)?;
    Ok(value
        .pointer("/error/code")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned())
}

fn count(seen: &Arc<Mutex<Vec<Seen>>>) -> usize {
    seen.lock().map_or(0, |list| list.len())
}

fn first(seen: &Arc<Mutex<Vec<Seen>>>) -> Option<Seen> {
    seen.lock().ok().and_then(|list| list.first().cloned())
}

fn header<'a>(seen: &'a Seen, name: &str) -> &'a str {
    seen.headers
        .get(name)
        .and_then(|value| value.to_str().ok())
        .unwrap_or_default()
}

async fn assert_not_found(app: &Router, path: &str) -> Result<(), Failure> {
    let response = send(app, request("GET", path)).await?;
    assert_eq!(response.status(), StatusCode::NOT_FOUND, "{path}");
    Ok(())
}

#[tokio::test]
async fn unknown_and_internal_paths_are_not_found_and_reach_nobody() -> Result<(), Failure> {
    let (identity, id_seen) = start(allow).await?;
    let (catalog, cat_seen) = start(|_| json_response(StatusCode::OK, "{}")).await?;
    let app = app(&identity, &catalog)?;
    assert_not_found(&app, "/internal/health").await?;
    assert_not_found(&app, "/api/notify/x").await?;
    assert_not_found(&app, "/media/x").await?;
    assert_not_found(&app, "/api/identity/../internal/x").await?;
    assert_eq!(count(&id_seen) + count(&cat_seen), 0);
    Ok(())
}

#[tokio::test]
async fn a_public_route_is_forwarded_without_asking_identity_and_with_clean_headers()
-> Result<(), Failure> {
    let (identity, id_seen) = start(allow).await?;
    let (catalog, cat_seen) = start(|_| json_response(StatusCode::OK, "{\"items\":[]}")).await?;
    let app = app(&identity, &catalog)?;
    let spoof = request("GET", "/api/catalog/books?q=x")
        .header("x-user-id", "attacker")
        .header("x-user-scopes", "manage_users")
        .header("authorization", "Service forged")
        .header("cookie", "__Host-session=abc");
    let response = send(&app, spoof).await?;
    assert_eq!(response.status(), StatusCode::OK);
    assert!(response.headers().contains_key("x-request-id"));
    assert_eq!(count(&id_seen), 0);
    let seen = first(&cat_seen).ok_or("catalog saw nothing")?;
    assert_eq!(seen.path, "/api/catalog/books");
    assert_eq!(header(&seen, "x-user-id"), "");
    assert!(
        header(&seen, "authorization").starts_with("Service ")
            && header(&seen, "authorization") != "Service forged"
    );
    assert_eq!(header(&seen, "cookie"), "");
    Ok(())
}

#[tokio::test]
async fn a_protected_route_needs_an_allow_and_gets_identity_headers() -> Result<(), Failure> {
    let (identity, id_seen) = start(allow).await?;
    let (catalog, cat_seen) = start(|_| json_response(StatusCode::OK, "{}")).await?;
    let app = app(&identity, &catalog)?;
    let call = request("GET", "/api/catalog/shelves").header("cookie", "__Host-session=tok");
    assert_eq!(send(&app, call).await?.status(), StatusCode::OK);
    let asked = first(&id_seen).ok_or("identity not asked")?;
    assert_eq!(asked.path, "/internal/authorize");
    assert_eq!(asked.method, Method::POST);
    let seen = first(&cat_seen).ok_or("catalog saw nothing")?;
    assert_eq!(header(&seen, "x-user-id"), "u-1");
    assert_eq!(header(&seen, "x-user-scopes"), "browse,read");
    assert_eq!(header(&seen, "x-grant-version"), "4");
    assert_eq!(header(&seen, "cookie"), "");
    Ok(())
}

fn unauthenticated(_path: &str) -> Response {
    json_response(StatusCode::UNAUTHORIZED, "{}")
}

fn inactive(_path: &str) -> Response {
    let body = r#"{"error":{"details":{"reason":"account_inactive"}}}"#;
    json_response(StatusCode::FORBIDDEN, body)
}

fn garbage(_path: &str) -> Response {
    json_response(StatusCode::OK, "garbage")
}

/// Identity answers with `answer`; the gateway must answer `status`/`code` and call nobody.
async fn assert_blocked(
    answer: fn(&str) -> Response,
    expected: (StatusCode, &str),
) -> Result<(), Failure> {
    let (identity, _) = start(answer).await?;
    let (catalog, cat_seen) = start(|_| json_response(StatusCode::OK, "{}")).await?;
    let app = app(&identity, &catalog)?;
    let response = send(&app, request("GET", "/api/catalog/shelves")).await?;
    assert_eq!(response.status(), expected.0);
    assert_eq!(error_code(response).await?, expected.1);
    assert_eq!(count(&cat_seen), 0);
    Ok(())
}

#[tokio::test]
async fn no_session_gives_401() -> Result<(), Failure> {
    assert_blocked(
        unauthenticated,
        (StatusCode::UNAUTHORIZED, "unauthenticated"),
    )
    .await
}

#[tokio::test]
async fn a_denied_session_gives_403() -> Result<(), Failure> {
    assert_blocked(inactive, (StatusCode::FORBIDDEN, "forbidden")).await
}

#[tokio::test]
async fn garbled_identity_answers_give_503() -> Result<(), Failure> {
    assert_blocked(
        garbage,
        (StatusCode::SERVICE_UNAVAILABLE, "peer_unavailable"),
    )
    .await
}

#[tokio::test]
async fn identity_down_gives_503_with_retry_after() -> Result<(), Failure> {
    let (catalog, cat_seen) = start(|_| json_response(StatusCode::OK, "{}")).await?;
    let app = app("http://127.0.0.1:1", &catalog)?;
    let response = send(&app, request("GET", "/api/catalog/shelves")).await?;
    assert_eq!(response.status(), StatusCode::SERVICE_UNAVAILABLE);
    assert!(response.headers().contains_key("retry-after"));
    assert_eq!(count(&cat_seen), 0);
    Ok(())
}

#[tokio::test]
async fn mutations_need_the_public_origin() -> Result<(), Failure> {
    let (identity, _) = start(allow).await?;
    let (catalog, cat_seen) = start(|_| json_response(StatusCode::OK, "{}")).await?;
    let app = app(&identity, &catalog)?;
    let missing = send(&app, request("POST", "/api/catalog/shelves")).await?;
    assert_eq!(error_code(missing).await?, "csrf_invalid");
    let wrong = request("POST", "/api/catalog/shelves").header("origin", "https://evil.test");
    assert_eq!(send(&app, wrong).await?.status(), StatusCode::FORBIDDEN);
    assert_eq!(count(&cat_seen), 0);
    let right = request("POST", "/api/catalog/shelves").header("origin", ORIGIN);
    assert_eq!(send(&app, right).await?.status(), StatusCode::OK);
    Ok(())
}

#[tokio::test]
async fn identity_csrf_denial_is_csrf_invalid() -> Result<(), Failure> {
    let (identity, _) = start(csrf_denied).await?;
    let (catalog, _) = start(|_| json_response(StatusCode::OK, "{}")).await?;
    let app = app(&identity, &catalog)?;
    let call = request("POST", "/api/catalog/shelves").header("origin", ORIGIN);
    assert_eq!(error_code(send(&app, call).await?).await?, "csrf_invalid");
    Ok(())
}

fn csrf_denied(_path: &str) -> Response {
    let body = r#"{"error":{"details":{"reason":"csrf_invalid"}}}"#;
    json_response(StatusCode::FORBIDDEN, body)
}

#[tokio::test]
async fn every_response_carries_security_headers_and_a_request_id() -> Result<(), Failure> {
    let (identity, _) = start(allow).await?;
    let (catalog, _) = start(|_| json_response(StatusCode::OK, "{}")).await?;
    let app = app(&identity, &catalog)?;
    assert_hardened(&app, "/nowhere").await?;
    assert_hardened(&app, "/api/catalog/books").await
}

async fn assert_hardened(app: &Router, path: &str) -> Result<(), Failure> {
    let response = send(app, request("GET", path)).await?;
    let headers = response.headers();
    assert!(headers.contains_key("content-security-policy"), "{path}");
    assert!(headers.contains_key("strict-transport-security"), "{path}");
    assert!(headers.contains_key("x-request-id"), "{path}");
    Ok(())
}

#[tokio::test]
async fn a_flood_from_one_address_is_limited_with_retry_after() -> Result<(), Failure> {
    let (identity, _) = start(allow).await?;
    let (catalog, _) = start(|_| json_response(StatusCode::OK, "{}")).await?;
    let app = app(&identity, &catalog)?;
    let last = burst(&app, "203.0.113.7", 80).await?;
    assert_eq!(last.status(), StatusCode::TOO_MANY_REQUESTS);
    assert!(last.headers().contains_key("retry-after"));
    assert_eq!(hit(&app, "198.51.100.9").await?.status(), StatusCode::OK);
    Ok(())
}

async fn hit(app: &Router, address: &str) -> Result<Response, Failure> {
    send(
        app,
        request("GET", "/api/catalog/books").header("x-forwarded-for", address),
    )
    .await
}

#[tokio::test]
async fn an_oversize_declared_body_is_refused_before_forwarding() -> Result<(), Failure> {
    let (identity, _) = start(allow).await?;
    let (catalog, cat_seen) = start(|_| json_response(StatusCode::OK, "{}")).await?;
    let app = app(&identity, &catalog)?;
    let big = request("POST", "/api/catalog/shelves")
        .header("origin", ORIGIN)
        .header("content-length", (2 * 1024 * 1024).to_string());
    assert_eq!(
        send(&app, big).await?.status(),
        StatusCode::PAYLOAD_TOO_LARGE
    );
    assert_eq!(count(&cat_seen), 0);
    Ok(())
}

/// Sends `count` requests from one address and returns the last response.
async fn burst(app: &Router, address: &str, count: usize) -> Result<Response, Failure> {
    let mut last = hit(app, address).await?;
    for _ in 1..count {
        last = hit(app, address).await?;
    }
    Ok(last)
}
