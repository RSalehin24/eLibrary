//! Notify's settings beyond the common ones: where identity is, the key it signs service tokens
//! with and the keys of the services that may call it (D-101). Mail relay settings are read by
//! `smtp::SmtpSettings`.

use platform_config::{ConfigError, ConfigSource, read_own_signing_key, read_peer_keys};
use platform_service_token::{
    KeyId, KeyOwner, KeyRing, ServiceName, SigningKey, TokenIssuer, Verifier,
};

type BuildError = Box<dyn std::error::Error + Send + Sync>;

const IDENTITY_KEY: &str = "ELIBRARY_UPSTREAM_IDENTITY";

/// What the sender and puller need to reach identity, and who may call notify.
pub struct NotifyConfig {
    pub identity_base: String,
    pub issuer: TokenIssuer,
    pub verifier: Verifier,
}

impl NotifyConfig {
    /// # Errors
    /// A missing or malformed setting, or an unreadable or short key.
    pub fn load(source: &impl ConfigSource) -> Result<Self, BuildError> {
        let invalid = || ConfigError::InvalidValue {
            key: IDENTITY_KEY.to_owned(),
        };
        let identity_base = source
            .get(IDENTITY_KEY)
            .ok_or_else(|| ConfigError::Missing {
                key: IDENTITY_KEY.to_owned(),
            })?;
        identity_base
            .starts_with("http://")
            .then_some(())
            .ok_or_else(invalid)?;
        let (key_id, secret) =
            read_own_signing_key(source)?.ok_or_else(|| ConfigError::Missing {
                key: "ELIBRARY_SERVICE_TOKEN_KEY_FILE".to_owned(),
            })?;
        let issuer = TokenIssuer::new(
            ServiceName::parse("notify")?,
            KeyId(key_id),
            SigningKey::from_hex(secret.expose())?,
        );
        Ok(Self {
            identity_base,
            issuer,
            verifier: Verifier::new(ServiceName::parse("notify")?, peer_ring(source)?),
        })
    }
}

fn peer_ring(source: &impl ConfigSource) -> Result<KeyRing, BuildError> {
    let mut ring = KeyRing::default();
    for peer in read_peer_keys(source)? {
        let owner = KeyOwner {
            service: ServiceName::parse(&peer.service)?,
            id: KeyId(peer.key_id),
        };
        ring = ring.with(owner, SigningKey::from_hex(peer.secret.expose())?);
    }
    Ok(ring)
}
