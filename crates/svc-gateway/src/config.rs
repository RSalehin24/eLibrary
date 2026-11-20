//! The gateway's settings: where each service is, the site's public origin (for the CSRF origin
//! check) and the key it signs service tokens with. All of it is checked at startup.

use std::collections::BTreeMap;

use platform_config::{ConfigError, ConfigSource, PublicOrigin, read_own_signing_key};
use platform_service_token::{KeyId, ServiceName, SigningKey, TokenIssuer};

use crate::routes::Upstream;

type BuildError = Box<dyn std::error::Error + Send + Sync>;

/// Everything the pipeline needs that comes from the environment.
pub struct GatewayConfig {
    pub origin: PublicOrigin,
    pub issuer: TokenIssuer,
    upstreams: BTreeMap<&'static str, String>,
}

fn key_of(upstream: Upstream) -> &'static str {
    match upstream {
        Upstream::Identity => "ELIBRARY_UPSTREAM_IDENTITY",
        Upstream::Catalog => "ELIBRARY_UPSTREAM_CATALOG",
        Upstream::Reader => "ELIBRARY_UPSTREAM_READER",
        Upstream::Ingestion => "ELIBRARY_UPSTREAM_INGESTION",
    }
}

const ALL: [Upstream; 4] = [
    Upstream::Identity,
    Upstream::Catalog,
    Upstream::Reader,
    Upstream::Ingestion,
];

/// `http://host:port` without a path; anything else is a configuration mistake.
fn base_url(source: &impl ConfigSource, upstream: Upstream) -> Result<String, ConfigError> {
    let key = key_of(upstream);
    let invalid = || ConfigError::InvalidValue {
        key: key.to_owned(),
    };
    let raw = source.get(key).ok_or_else(|| ConfigError::Missing {
        key: key.to_owned(),
    })?;
    let host = raw.strip_prefix("http://").ok_or_else(invalid)?;
    let plain = host
        .bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || b".-:".contains(&byte));
    (!host.is_empty() && plain)
        .then_some(raw)
        .ok_or_else(invalid)
}

impl GatewayConfig {
    /// # Errors
    /// A missing or malformed setting, or an unreadable or short signing key.
    pub fn load(source: &impl ConfigSource) -> Result<Self, BuildError> {
        let upstreams = ALL
            .into_iter()
            .map(|upstream| base_url(source, upstream).map(|url| (upstream.name(), url)))
            .collect::<Result<BTreeMap<_, _>, _>>()?;
        let (key_id, secret) =
            read_own_signing_key(source)?.ok_or_else(|| ConfigError::Missing {
                key: "ELIBRARY_SERVICE_TOKEN_KEY_FILE".to_owned(),
            })?;
        let issuer = TokenIssuer::new(
            ServiceName::parse("gateway")?,
            KeyId(key_id),
            SigningKey::from_hex(secret.expose())?,
        );
        Ok(Self {
            origin: PublicOrigin::load(source)?,
            issuer,
            upstreams,
        })
    }

    /// The base URL of a service, such as `http://identity:8080`.
    #[must_use]
    pub fn base(&self, upstream: Upstream) -> &str {
        self.upstreams
            .get(upstream.name())
            .map_or("", String::as_str)
    }
}
