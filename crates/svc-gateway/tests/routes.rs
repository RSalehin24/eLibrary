//! Integration tests for the gateway route table (INV-GWY-001, INV-GWY-003).

use axum::http::{Method, Uri};
use proptest::prelude::*;
use svc_gateway::routes::{PUBLIC_ROUTES, RouteClass, Routed, Upstream, route};

fn routed(method: &Method, path: &str) -> Option<Routed> {
    route(method, &Uri::try_from(path).ok()?)
}

fn class_of(method: &Method, path: &str) -> Option<RouteClass> {
    routed(method, path).map(|r| r.class)
}

#[test]
fn inv_gwy_003_every_public_route_is_public() {
    let cases = [
        (Method::POST, "/api/identity/auth/sign-in"),
        (Method::POST, "/api/identity/auth/totp/verify"),
        (Method::POST, "/api/identity/invites/accept"),
        (Method::POST, "/api/identity/password-reset/request"),
        (Method::POST, "/api/identity/password-reset/confirm"),
        (Method::GET, "/api/catalog/books"),
        (Method::GET, "/api/catalog/books?q=x&limit=10"),
        (Method::GET, "/api/catalog/books/some-slug"),
        (Method::GET, "/api/catalog/books/some-slug/cover"),
        (Method::GET, "/api/catalog/browse/writers"),
        (Method::GET, "/api/catalog/browse/writers/42"),
    ];
    for (method, path) in cases {
        assert_eq!(class_of(&method, path), Some(RouteClass::Public), "{path}");
    }
}

#[test]
fn inv_gwy_003_public_table_is_exactly_the_documented_list() {
    let mut table: Vec<String> = PUBLIC_ROUTES
        .iter()
        .map(|(m, p)| format!("{m} {p}"))
        .collect();
    table.sort();
    let mut expected = vec![
        "POST /api/identity/auth/sign-in",
        "POST /api/identity/auth/totp/verify",
        "POST /api/identity/invites/accept",
        "POST /api/identity/password-reset/request",
        "POST /api/identity/password-reset/confirm",
        "GET /api/catalog/books",
        "GET /api/catalog/books/{slug}",
        "GET /api/catalog/books/{slug}/cover",
        "GET /api/catalog/browse/{facet}",
        "GET /api/catalog/browse/{facet}/{id}",
    ];
    expected.sort_unstable();
    assert_eq!(table, expected);
}

#[test]
fn inv_gwy_003_no_preview_reading_or_download_route_is_public() {
    let banned = ["/read", "/preview", "/ticket", "/download"];
    let clean = |p: &&(Method, &str)| !banned.iter().any(|b| p.1.contains(b));
    assert_eq!(
        PUBLIC_ROUTES.iter().filter(clean).count(),
        PUBLIC_ROUTES.len()
    );
    for path in [
        "/api/catalog/books/x/preview",
        "/api/catalog/books/x/read",
        "/api/catalog/books/x/download",
        "/api/catalog/books/x/ticket",
        "/api/reader/books/x",
    ] {
        assert_eq!(class_of(&Method::GET, path), Some(RouteClass::Protected));
    }
}

#[test]
fn protected_routes_and_upstreams() {
    let cases = [
        (Method::GET, "/api/identity/me", Upstream::Identity),
        (Method::POST, "/api/catalog/books", Upstream::Catalog),
        (Method::GET, "/api/reader/books/x/package", Upstream::Reader),
        (Method::GET, "/api/ingestion/events", Upstream::Ingestion),
    ];
    for (method, path, upstream) in cases {
        let r = routed(&method, path);
        assert_eq!(r.as_ref().map(|r| r.class), Some(RouteClass::Protected));
        assert_eq!(r.map(|r| r.upstream), Some(upstream));
    }
}

#[test]
fn unrouted_paths_are_none() {
    for path in [
        "/internal/health",
        "/api/notify/x",
        "/api/notify",
        "/media/x",
        "/api/unknown/x",
        "/api/",
        "/api",
        "/",
        "/api/identityx/me",
        "/API/identity/me",
    ] {
        assert!(routed(&Method::GET, path).is_none(), "{path}");
    }
}

#[test]
fn traversal_and_encoding_attacks_are_none() {
    let long = format!("/api/catalog/{}", "a".repeat(2048));
    let attacks = [
        "/api/identity/../internal/health",
        "/api/identity/./me",
        "/api/identity/me/..",
        "/api/identity//me",
        "/api/identity/me//",
        "/api/identity/%2e%2e/internal",
        "/api/identity/%2E%2E/internal",
        "/api/identity/.%2e/internal",
        "/api/identity/a%2fb",
        "/api/identity/a%2Fb",
        "/api/identity/a%5cb",
        "/api/identity/a%5Cb",
        "/api/identity/a%00b",
        "/api/identity/a%252e",
        "/api/identity/a%zz",
        "/api/identity/a%",
        "/api/identity/a%4",
        "/api/identity/a\\b",
        "/api/identity/caf\u{e9}",
        "/api/identity/%0d%0a",
        "/api/identity/a\u{0}b",
        "/api/identity/a\tb",
        "/api/identity/a b",
        long.as_str(),
    ];
    for path in attacks {
        // Some of these are not valid URIs at all; both outcomes are a refusal.
        assert!(routed(&Method::GET, path).is_none(), "{path:?}");
    }
}

#[test]
fn valid_percent_escapes_are_routed() {
    let r = routed(&Method::GET, "/api/catalog/books/%E0%A6%85");
    assert_eq!(r.map(|r| r.class), Some(RouteClass::Public));
}

proptest! {
    #[test]
    fn inv_gwy_001_unknown_prefix_is_never_routed(path in "/[a-z/]{0,40}") {
        let known = ["/api/identity", "/api/catalog", "/api/reader", "/api/ingestion"];
        prop_assume!(!known.iter().any(|k| path == *k || path.starts_with(&format!("{k}/"))));
        if let Ok(uri) = Uri::try_from(path.as_str()) {
            prop_assert!(route(&Method::GET, &uri).is_none());
        }
    }

    #[test]
    fn route_never_panics(path in "\\PC{0,200}") {
        if let Ok(uri) = Uri::try_from(path.as_str()) {
            let _ = route(&Method::GET, &uri);
            let _ = route(&Method::POST, &uri);
        }
    }

    #[test]
    fn routed_paths_are_clean(tail in "[a-zA-Z0-9%./_-]{0,60}") {
        let path = format!("/api/catalog/{tail}");
        let routed = Uri::try_from(path.as_str()).ok().and_then(|u| route(&Method::GET, &u));
        if let Some(r) = routed {
            prop_assert!(!r.path_and_query.contains("//"));
            prop_assert!(!r.path_and_query.contains("/../"));
            prop_assert!(!r.path_and_query.ends_with("/.."));
            prop_assert!(!r.path_and_query.to_ascii_lowercase().contains("%2f"));
        }
    }
}
