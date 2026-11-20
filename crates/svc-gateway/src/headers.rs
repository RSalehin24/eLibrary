//! Gateway header handling: request ids, stripping untrusted client headers, stamping identity,
//! response security headers and log-safe redaction (REQ-GWY-004, REQ-GWY-006, REQ-GWY-009).

use axum::http::header::{
    AUTHORIZATION, CACHE_CONTROL, CONNECTION, CONTENT_SECURITY_POLICY, REFERRER_POLICY, SERVER,
    STRICT_TRANSPORT_SECURITY, X_CONTENT_TYPE_OPTIONS, X_FRAME_OPTIONS,
};
use axum::http::{HeaderMap, HeaderName, HeaderValue};
use platform_random::RandomSource;

const MAX_REQUEST_ID_LEN: usize = 64;
const FALLBACK_REQUEST_ID: &str = "00000000-0000-7000-8000-000000000000";
const REQUEST_ID: &str = "x-request-id";
const USER_ID: &str = "x-user-id";
const USER_SCOPES: &str = "x-user-scopes";
const GRANT_VERSION: &str = "x-grant-version";
const PREFIXES: [&str; 3] = ["x-user-", "x-grant-", "x-internal-"];
const HOP_BY_HOP: [&str; 8] = [
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
];
const SECRET_NAMES: [&str; 4] = ["cookie", "authorization", "x-csrf-token", "set-cookie"];
const REDACTED: &str = "<redacted>";

/// A validated correlation id: a hyphenated UUID of at most 64 characters.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RequestId(String);

impl RequestId {
    /// Keep the client's id when it is a UUID, otherwise generate a `UUIDv7`.
    #[must_use]
    pub fn from_header(
        value: Option<&HeaderValue>,
        now_millis: u64,
        random: &impl RandomSource,
    ) -> Self {
        let kept = value
            .and_then(|v| v.to_str().ok())
            .filter(|t| is_uuid_text(t))
            .map(str::to_owned);
        Self(kept.unwrap_or_else(|| generate(now_millis, random)))
    }

    /// The id as text.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

fn generate(now_millis: u64, random: &impl RandomSource) -> String {
    platform_random::uuid_v7(now_millis, random)
        .map_or_else(|_| FALLBACK_REQUEST_ID.to_owned(), |id| id.to_string())
}

fn is_uuid_text(text: &str) -> bool {
    const GROUPS: [usize; 5] = [8, 4, 4, 4, 12];
    if text.len() > MAX_REQUEST_ID_LEN || !text.is_ascii() {
        return false;
    }
    let parts: Vec<&str> = text.split('-').collect();
    parts.len() == GROUPS.len()
        && parts
            .iter()
            .zip(GROUPS)
            .all(|(part, len)| part.len() == len && part.bytes().all(|b| b.is_ascii_hexdigit()))
}

/// The caller as proven by identity, stamped onto upstream requests.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Identity {
    pub user_id: String,
    pub scopes: Vec<String>,
    pub grant_version: i64,
}

fn is_untrusted(name: &HeaderName, headers: &HeaderMap) -> bool {
    let text = name.as_str();
    if text == REQUEST_ID || PREFIXES.iter().any(|p| text.starts_with(p)) {
        return true;
    }
    HOP_BY_HOP.contains(&text) || (*name == AUTHORIZATION && has_service_scheme(headers))
}

fn has_service_scheme(headers: &HeaderMap) -> bool {
    headers.get_all(AUTHORIZATION).iter().any(|v| {
        v.as_bytes()
            .get(..8)
            .is_some_and(|s| s.eq_ignore_ascii_case(b"service "))
    })
}

fn connection_named(headers: &HeaderMap) -> Vec<HeaderName> {
    headers
        .get_all(CONNECTION)
        .iter()
        .filter_map(|v| v.to_str().ok())
        .flat_map(|v| v.split(','))
        .filter_map(|token| HeaderName::from_bytes(token.trim().as_bytes()).ok())
        .collect()
}

/// Remove client-supplied identity/internal headers and hop-by-hop headers.
pub fn strip_untrusted(headers: &mut HeaderMap) {
    let mut doomed = connection_named(headers);
    doomed.extend(
        headers
            .keys()
            .filter(|name| is_untrusted(name, headers))
            .cloned(),
    );
    for name in doomed {
        headers.remove(name);
    }
}

fn set_text(headers: &mut HeaderMap, name: &'static str, value: &str) {
    if let Ok(value) = HeaderValue::from_str(value) {
        headers.insert(HeaderName::from_static(name), value);
    }
}

/// Set the identity headers (call after [`strip_untrusted`]).
pub fn stamp_identity(headers: &mut HeaderMap, who: &Identity) {
    set_text(headers, USER_ID, &who.user_id);
    set_text(headers, USER_SCOPES, &who.scopes.join(","));
    set_text(headers, GRANT_VERSION, &who.grant_version.to_string());
}

/// Set `X-Request-Id`.
pub fn stamp_request_id(headers: &mut HeaderMap, id: &RequestId) {
    set_text(headers, REQUEST_ID, id.as_str());
}

fn set_if_absent(headers: &mut HeaderMap, name: HeaderName, value: &'static str) {
    if !headers.contains_key(&name) {
        headers.insert(name, HeaderValue::from_static(value));
    }
}

/// Security headers for every API response; upstream values win except the two forced ones.
pub fn apply_security_headers(headers: &mut HeaderMap) {
    set_if_absent(
        headers,
        CONTENT_SECURITY_POLICY,
        "default-src 'none'; frame-ancestors 'none'",
    );
    set_if_absent(
        headers,
        STRICT_TRANSPORT_SECURITY,
        "max-age=63072000; includeSubDomains",
    );
    set_if_absent(headers, REFERRER_POLICY, "no-referrer");
    set_if_absent(headers, CACHE_CONTROL, "no-store");
    headers.insert(X_FRAME_OPTIONS, HeaderValue::from_static("DENY"));
    headers.insert(X_CONTENT_TYPE_OPTIONS, HeaderValue::from_static("nosniff"));
    headers.remove(SERVER);
    headers.remove("x-powered-by");
}

fn is_secret(name: &str) -> bool {
    SECRET_NAMES.contains(&name) || name.contains("ticket")
}

/// Log-safe view: header names, with `<redacted>` marking secret-bearing ones.
#[must_use]
pub fn redacted(headers: &HeaderMap) -> Vec<String> {
    headers.keys().map(|name| describe(name.as_str())).collect()
}

fn describe(name: &str) -> String {
    if is_secret(name) {
        format!("{name}: {REDACTED}")
    } else {
        name.to_owned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use platform_random::SequenceRandom;

    #[test]
    fn valid_uuid_is_kept_and_junk_is_replaced() {
        let rnd = SequenceRandom::default();
        let ok = HeaderValue::from_static("123e4567-e89b-12d3-a456-426614174000");
        assert_eq!(
            RequestId::from_header(Some(&ok), 1, &rnd).as_str(),
            "123e4567-e89b-12d3-a456-426614174000"
        );
        let bad = HeaderValue::from_static("not-a-uuid");
        let made = RequestId::from_header(Some(&bad), 1, &rnd);
        assert!(is_uuid_text(made.as_str()));
        assert_ne!(made.as_str(), "not-a-uuid");
        assert!(is_uuid_text(RequestId::from_header(None, 1, &rnd).as_str()));
    }

    #[test]
    fn strip_removes_service_auth_but_keeps_cookie_and_bearer() {
        let mut h = HeaderMap::new();
        h.insert("authorization", HeaderValue::from_static("sErViCe abc"));
        h.insert("cookie", HeaderValue::from_static("s=1"));
        h.insert("connection", HeaderValue::from_static("x-secret, close"));
        h.insert("x-secret", HeaderValue::from_static("1"));
        strip_untrusted(&mut h);
        assert!(h.contains_key("cookie"));
        assert!(!h.contains_key("authorization"));
        assert!(!h.contains_key("x-secret"));
        assert!(!h.contains_key("connection"));
        let mut b = HeaderMap::new();
        b.insert("authorization", HeaderValue::from_static("Bearer t"));
        strip_untrusted(&mut b);
        assert!(b.contains_key("authorization"));
    }

    #[test]
    fn redaction_hides_secret_bearing_headers() {
        let mut h = HeaderMap::new();
        h.insert("cookie", HeaderValue::from_static("secret"));
        h.insert("x-ticket-id", HeaderValue::from_static("secret"));
        h.insert("accept", HeaderValue::from_static("secret"));
        let out = redacted(&h).join("|");
        assert!(!out.contains("secret"));
        assert!(out.contains("cookie: <redacted>"));
        assert!(out.contains("x-ticket-id: <redacted>"));
    }
}
