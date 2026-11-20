//! Route table of the gateway (REQ-GWY-001, REQ-GWY-003).
//!
//! `route` maps a request to an upstream and a route class, or to `None` (answer 404). The public
//! allow-list is a closed constant table; every other `/api/<service>/*` path needs a session.
//! Paths that could be read differently by the gateway and an upstream (dot segments, empty
//! segments, encoded separators, control or non-ASCII characters) are never routed.

use axum::http::{Method, Uri};

/// Longest path (in bytes, query excluded) that is routed.
pub const MAX_PATH_BYTES: usize = 2048;

/// The backend services reachable through the gateway. Notify has no public route.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Upstream {
    /// Accounts, sessions, grants.
    Identity,
    /// Books, metadata, shelves.
    Catalog,
    /// Reading packages.
    Reader,
    /// Ingestion console.
    Ingestion,
}

impl Upstream {
    /// The service name used in tokens and logs.
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::Identity => "identity",
            Self::Catalog => "catalog",
            Self::Reader => "reader",
            Self::Ingestion => "ingestion",
        }
    }

    fn from_segment(segment: &str) -> Option<Self> {
        match segment {
            "identity" => Some(Self::Identity),
            "catalog" => Some(Self::Catalog),
            "reader" => Some(Self::Reader),
            "ingestion" => Some(Self::Ingestion),
            _ => None,
        }
    }
}

/// Whether a route skips the session check.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RouteClass {
    /// On the closed allow-list: no session needed.
    Public,
    /// Everything else: identity must allow the request.
    Protected,
}

/// A routed request.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Routed {
    /// The service that receives the request.
    pub upstream: Upstream,
    /// Public or protected.
    pub class: RouteClass,
    /// The original path (unchanged, still under `/api/<service>/`) plus the query string.
    pub path_and_query: String,
}

/// The closed public allow-list (REQ-GWY-003, REQ-IDN-014, D-34): each entry is a method and a
/// full path pattern; `{name}` matches exactly one non-empty segment. There is deliberately no
/// preview, reading, ticket or download route.
pub const PUBLIC_ROUTES: &[(Method, &str)] = &[
    (Method::POST, "/api/identity/auth/sign-in"),
    (Method::POST, "/api/identity/auth/totp/verify"),
    (Method::POST, "/api/identity/invites/accept"),
    (Method::POST, "/api/identity/password-reset/request"),
    (Method::POST, "/api/identity/password-reset/confirm"),
    (Method::GET, "/api/catalog/books"),
    (Method::GET, "/api/catalog/books/{slug}"),
    (Method::GET, "/api/catalog/books/{slug}/cover"),
    (Method::GET, "/api/catalog/browse/{facet}"),
    (Method::GET, "/api/catalog/browse/{facet}/{id}"),
];

/// Routes a request. `None` means the gateway answers 404.
#[must_use]
pub fn route(method: &Method, uri: &Uri) -> Option<Routed> {
    let path = uri.path();
    if !path_is_clean(path) {
        return None;
    }
    let rest = path.strip_prefix("/api/")?;
    let service = rest.split('/').next()?;
    let upstream = Upstream::from_segment(service)?;
    let tail = rest.get(service.len()..)?;
    if !tail_is_well_formed(tail) {
        return None;
    }
    let class = classify(method, path);
    let path_and_query = uri
        .path_and_query()
        .map_or_else(|| path.to_owned(), |pq| pq.as_str().to_owned());
    Some(Routed {
        upstream,
        class,
        path_and_query,
    })
}

/// After the service name only `""`, `"/"` or `"/seg/..."` with no empty segment may follow.
fn tail_is_well_formed(tail: &str) -> bool {
    match tail.strip_prefix('/') {
        None => tail.is_empty(),
        Some("") => true,
        Some(inner) => inner
            .split('/')
            .all(|s| !s.is_empty() && s != "." && s != ".."),
    }
}

fn classify(method: &Method, path: &str) -> RouteClass {
    if PUBLIC_ROUTES
        .iter()
        .any(|(m, pattern)| m == method && pattern_matches(pattern, path))
    {
        RouteClass::Public
    } else {
        RouteClass::Protected
    }
}

fn pattern_matches(pattern: &str, path: &str) -> bool {
    pattern.split('/').count() == path.split('/').count()
        && pattern
            .split('/')
            .zip(path.split('/'))
            .all(|(want, got)| segment_matches(want, got))
}

fn segment_matches(pattern: &str, segment: &str) -> bool {
    if pattern.starts_with('{') && pattern.ends_with('}') {
        !segment.is_empty()
    } else {
        pattern == segment
    }
}

fn path_is_clean(path: &str) -> bool {
    path.len() <= MAX_PATH_BYTES
        && path.bytes().all(plain_byte)
        && !has_dangerous_escape(path.as_bytes())
        && !path.split('/').skip(1).any(|s| s == "." || s == "..")
}

/// Printable ASCII only; backslash is never allowed.
fn plain_byte(b: u8) -> bool {
    (0x21..=0x7e).contains(&b) && b != b'\\'
}

/// A `%` must start a valid escape, and the escapes that hide separators, dots, NUL or a second
/// level of encoding (`%2e`, `%2f`, `%5c`, `%25`, and encoded control characters) are refused in any letter case.
fn has_dangerous_escape(bytes: &[u8]) -> bool {
    bytes
        .iter()
        .enumerate()
        .any(|(i, b)| *b == b'%' && !escape_is_safe(bytes.get(i + 1..i + 3).unwrap_or_default()))
}

fn escape_is_safe(hex: &[u8]) -> bool {
    let value = std::str::from_utf8(hex)
        .ok()
        .filter(|h| h.bytes().all(|b| b.is_ascii_hexdigit()))
        .and_then(|h| u8::from_str_radix(h, 16).ok());
    value.is_some_and(|v| v > 0x1f && v != 0x7f && !b"./\\%".contains(&v))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn routed(method: &Method, path: &str) -> Option<Routed> {
        route(method, &Uri::try_from(path).ok()?)
    }

    #[test]
    fn upstream_names_are_the_token_names() {
        assert_eq!(Upstream::Identity.name(), "identity");
        assert_eq!(Upstream::Catalog.name(), "catalog");
        assert_eq!(Upstream::Reader.name(), "reader");
        assert_eq!(Upstream::Ingestion.name(), "ingestion");
    }

    #[test]
    fn inv_gwy_001_query_is_kept_and_path_unchanged() {
        let r = routed(&Method::GET, "/api/catalog/books?q=abc&limit=5");
        assert_eq!(
            r.map(|r| r.path_and_query),
            Some("/api/catalog/books?q=abc&limit=5".to_owned())
        );
    }

    #[test]
    fn trailing_slash_after_service_is_protected() {
        let r = routed(&Method::GET, "/api/identity/");
        assert_eq!(r.map(|r| r.class), Some(RouteClass::Protected));
        assert!(routed(&Method::GET, "/api/identity").is_some());
        assert!(routed(&Method::GET, "/api/identity/me/").is_none());
    }

    #[test]
    fn method_matters_for_public_routes() {
        let r = routed(&Method::GET, "/api/identity/auth/sign-in");
        assert_eq!(r.map(|r| r.class), Some(RouteClass::Protected));
    }

    #[test]
    fn mixed_case_escape_is_refused() {
        assert!(routed(&Method::GET, "/api/catalog/books/%2E%2e").is_none());
        assert!(routed(&Method::GET, "/api/catalog/books/%e0%A6%85").is_some());
    }
}
