use crate::{ConfigError, ConfigSource};

const KEY: &str = "ELIBRARY_PUBLIC_ORIGIN";

/// The https address the site is served at, e.g. `https://library.example`, used to build the
/// links in emails (D-100). No path, query, fragment or credentials.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicOrigin(String);

impl PublicOrigin {
    /// # Errors
    /// The setting is missing, not an `https://host[:port]` origin, or has extra parts.
    pub fn load(source: &impl ConfigSource) -> Result<Self, ConfigError> {
        let invalid = || ConfigError::InvalidValue {
            key: KEY.to_owned(),
        };
        let raw = source.get(KEY).ok_or_else(|| ConfigError::Missing {
            key: KEY.to_owned(),
        })?;
        let origin = raw.strip_suffix('/').unwrap_or(&raw);
        let host = origin.strip_prefix("https://").ok_or_else(invalid)?;
        let plain = host
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b".-:[]".contains(&byte));
        (!host.is_empty() && plain)
            .then(|| Self(origin.to_owned()))
            .ok_or_else(invalid)
    }

    /// The origin followed by `path` (which starts with `/`).
    #[must_use]
    pub fn url(&self, path: &str) -> String {
        format!("{}{path}", self.0)
    }
}

#[cfg(test)]
mod tests {
    use super::PublicOrigin;
    use crate::{ConfigError, MapSource};

    fn source(value: Option<&str>) -> MapSource {
        let empty = MapSource::default();
        match value {
            Some(text) => empty.with("ELIBRARY_PUBLIC_ORIGIN", text),
            None => empty,
        }
    }

    fn load(value: Option<&str>) -> Result<PublicOrigin, ConfigError> {
        PublicOrigin::load(&source(value))
    }

    fn is_invalid(value: &str) -> bool {
        matches!(load(Some(value)), Err(ConfigError::InvalidValue { .. }))
    }

    #[test]
    fn accepts_an_https_origin_with_or_without_port_and_slash() {
        let origin = load(Some("https://library.example:8443/"));
        assert_eq!(
            origin.map(|origin| origin.url("/accept?t=1")),
            Ok("https://library.example:8443/accept?t=1".to_owned())
        );
        assert!(load(Some("https://127.0.0.1:8443")).is_ok());
    }

    #[test]
    fn refuses_missing_http_and_extra_parts() {
        assert!(matches!(load(None), Err(ConfigError::Missing { .. })));
        let bad = [
            "http://library.example",
            "library.example",
            "https://",
            "https://user@library.example",
            "https://library.example/app",
            "https://library.example?x=1",
            "https://library .example",
        ];
        let accepted: Vec<&str> = bad.into_iter().filter(|text| !is_invalid(text)).collect();
        assert!(accepted.is_empty(), "{accepted:?}");
    }
}
