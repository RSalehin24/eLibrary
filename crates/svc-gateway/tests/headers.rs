//! Integration and property tests for gateway header handling (REQ-GWY-004/006/009).

use axum::http::{HeaderMap, HeaderName, HeaderValue};
use proptest::prelude::*;
use svc_gateway::headers::{
    Identity, RequestId, apply_security_headers, stamp_identity, stamp_request_id, strip_untrusted,
};

fn identity() -> Identity {
    Identity {
        user_id: "u-1".to_owned(),
        scopes: vec!["read".to_owned(), "write".to_owned()],
        grant_version: 7,
    }
}

fn name_strategy() -> impl Strategy<Value = String> {
    prop_oneof![
        "[a-zA-Z][a-zA-Z0-9-]{0,12}",
        "[xX]-[uU][sS][eE][rR]-[a-zA-Z]{0,6}",
        "[xX]-[gG][rR][aA][nN][tT]-[a-zA-Z]{0,6}",
        "[xX]-[iI][nN][tT][eE][rR][nN][aA][lL]-[a-zA-Z]{0,6}",
        Just("X-User-Id".to_owned()),
        Just("x-USER-id".to_owned()),
        Just("X-Request-Id".to_owned()),
    ]
}

proptest! {
    #[test]
    fn only_stamped_identity_headers_survive(
        pairs in proptest::collection::vec((name_strategy(), "[ -~]{0,20}"), 0..16)
    ) {
        let mut h = HeaderMap::new();
        for (n, v) in pairs {
            if let (Ok(n), Ok(v)) = (HeaderName::from_bytes(n.as_bytes()), HeaderValue::from_str(&v)) {
                h.append(n, v);
            }
        }
        strip_untrusted(&mut h);
        stamp_identity(&mut h, &identity());
        for name in h.keys() {
            let t = name.as_str();
            if t.starts_with("x-user-") || t.starts_with("x-grant-") || t.starts_with("x-internal-") {
                prop_assert!(["x-user-id", "x-user-scopes", "x-grant-version"].contains(&t));
            }
        }
        prop_assert_eq!(h.get_all("x-user-id").iter().count(), 1);
        prop_assert_eq!(h.get("x-user-id"), Some(&HeaderValue::from_static("u-1")));
        prop_assert!(!h.contains_key("x-request-id"));
    }

    #[test]
    fn request_id_never_panics_and_is_always_uuid(raw in "[ -~]{0,100}") {
        let rnd = platform_random::SequenceRandom::default();
        let value = HeaderValue::from_str(&raw).ok();
        let id = RequestId::from_header(value.as_ref(), 5, &rnd);
        prop_assert!(id.as_str().len() <= 64);
        prop_assert_eq!(id.as_str().split('-').count(), 5);
    }
}

#[test]
fn client_user_id_is_replaced_by_stamp() {
    let mut h = HeaderMap::new();
    h.append("x-user-id", HeaderValue::from_static("evil"));
    h.append("X-User-Id", HeaderValue::from_static("evil2"));
    strip_untrusted(&mut h);
    assert!(!h.contains_key("x-user-id"));
    stamp_identity(&mut h, &identity());
    stamp_request_id(
        &mut h,
        &RequestId::from_header(None, 1, &platform_random::SequenceRandom::default()),
    );
    assert_eq!(
        h.get("x-user-scopes"),
        Some(&HeaderValue::from_static("read,write"))
    );
    assert_eq!(
        h.get("x-grant-version"),
        Some(&HeaderValue::from_static("7"))
    );
    assert!(h.contains_key("x-request-id"));
}

#[test]
fn security_headers_on_empty_response() {
    let mut h = HeaderMap::new();
    apply_security_headers(&mut h);
    for name in [
        "content-security-policy",
        "strict-transport-security",
        "x-frame-options",
        "referrer-policy",
        "x-content-type-options",
        "cache-control",
    ] {
        assert!(h.contains_key(name), "{name}");
    }
}

#[test]
fn upstream_values_kept_except_forced_ones() {
    let mut h = HeaderMap::new();
    h.insert(
        "content-security-policy",
        HeaderValue::from_static("default-src 'self'"),
    );
    h.insert("cache-control", HeaderValue::from_static("max-age=5"));
    h.insert("x-frame-options", HeaderValue::from_static("SAMEORIGIN"));
    h.insert("server", HeaderValue::from_static("x"));
    h.insert("x-powered-by", HeaderValue::from_static("y"));
    apply_security_headers(&mut h);
    assert_eq!(
        h.get("content-security-policy"),
        Some(&HeaderValue::from_static("default-src 'self'"))
    );
    assert_eq!(
        h.get("cache-control"),
        Some(&HeaderValue::from_static("max-age=5"))
    );
    assert_eq!(
        h.get("x-frame-options"),
        Some(&HeaderValue::from_static("DENY"))
    );
    assert!(!h.contains_key("server") && !h.contains_key("x-powered-by"));
}
