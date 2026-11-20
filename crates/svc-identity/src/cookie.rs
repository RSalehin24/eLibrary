//! The session cookie: `__Host-` prefixed, so it is `Secure`, host-only and path `/`.

use axum::http::header::COOKIE;
use axum::http::{HeaderMap, HeaderValue};

use crate::session::ABSOLUTE_TIMEOUT;

const NAME: &str = "__Host-session";

/// The session token from the request's cookies, if one is present.
pub(crate) fn session_token(headers: &HeaderMap) -> Option<&str> {
    headers
        .get_all(COOKIE)
        .iter()
        .filter_map(|value| value.to_str().ok())
        .flat_map(|line| line.split(';'))
        .filter_map(|pair| pair.trim().split_once('='))
        .find(|(name, _)| *name == NAME)
        .map(|(_, value)| value)
        .filter(|value| !value.is_empty())
}

/// `Set-Cookie` for a new session; the token is hex, so it needs no quoting.
pub(crate) fn set(token: &str) -> Option<HeaderValue> {
    let max_age = ABSOLUTE_TIMEOUT.as_secs();
    HeaderValue::from_str(&format!(
        "{NAME}={token}; Max-Age={max_age}; Path=/; Secure; HttpOnly; SameSite=Lax"
    ))
    .ok()
}

pub(crate) fn clear() -> HeaderValue {
    HeaderValue::from_static("__Host-session=; Max-Age=0; Path=/; Secure; HttpOnly; SameSite=Lax")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn headers(lines: &[&str]) -> Result<HeaderMap, Box<dyn std::error::Error>> {
        let values = lines
            .iter()
            .map(|line| HeaderValue::from_str(line))
            .collect::<Result<Vec<_>, _>>()?;
        let mut map = HeaderMap::new();
        map.extend(values.into_iter().map(|value| (COOKIE, value)));
        Ok(map)
    }

    #[test]
    fn finds_the_session_among_other_cookies() -> Result<(), Box<dyn std::error::Error>> {
        let map = headers(&["theme=dark; __Host-session=abc123", "x=y"])?;
        assert_eq!(session_token(&map), Some("abc123"));
        Ok(())
    }

    #[test]
    fn ignores_a_lookalike_name_and_an_empty_value() -> Result<(), Box<dyn std::error::Error>> {
        assert_eq!(session_token(&headers(&["session=abc"])?), None);
        assert_eq!(session_token(&headers(&["__Host-session="])?), None);
        Ok(())
    }
}
