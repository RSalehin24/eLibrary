use std::time::Duration;

use hmac::{Hmac, KeyInit, Mac};
use platform_time::Instant;
use sha2::Sha256;

use crate::{KeyId, KeyRing, ServiceName, SigningKey, TokenError, hex};

/// A token may not live longer than this (service-auth spec).
pub const MAX_LIFETIME: Duration = Duration::from_secs(60);
const CLOCK_SKEW: Duration = Duration::from_secs(5);
const VERSION: &str = "v1";
const AUTHORIZATION_SCHEME: &str = "Service ";

type HmacSha256 = Hmac<Sha256>;

/// The text sent after `Authorization: Service `.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Token(String);

impl Token {
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// The token inside an `Authorization` header value, or `None` for any other scheme.
#[must_use]
pub fn bearer_token(header_value: &str) -> Option<&str> {
    header_value.strip_prefix(AUTHORIZATION_SCHEME)
}

/// What a caller asks for when minting a token.
#[derive(Debug, Clone, Copy)]
pub struct IssueRequest<'a> {
    pub callee: &'a ServiceName,
    pub now: Instant,
    pub lifetime: Duration,
}

/// Mints tokens as one service, with that service's own key.
#[derive(Debug, Clone)]
pub struct TokenIssuer {
    caller: ServiceName,
    key_id: KeyId,
    key: SigningKey,
}

impl TokenIssuer {
    #[must_use]
    pub fn new(caller: ServiceName, key_id: KeyId, key: SigningKey) -> Self {
        Self {
            caller,
            key_id,
            key,
        }
    }

    /// `None` only when the time range overflows.
    #[must_use]
    pub fn issue(&self, request: IssueRequest<'_>) -> Option<Token> {
        let expires = request.now.checked_add(request.lifetime)?;
        let signed = format!(
            "{VERSION}.{}.{}.{}.{}.{}",
            self.key_id.0,
            self.caller,
            request.callee,
            request.now.unix_seconds(),
            expires.unix_seconds()
        );
        let mac = sign(&self.key, &signed)?;
        Some(Token(format!("{signed}.{}", hex::encode(&mac))))
    }
}

/// Checks tokens presented to one service.
#[derive(Debug, Clone)]
pub struct Verifier {
    callee: ServiceName,
    keys: KeyRing,
}

impl Verifier {
    #[must_use]
    pub fn new(callee: ServiceName, keys: KeyRing) -> Self {
        Self { callee, keys }
    }

    /// Returns the verified caller. Checks, in order: shape, key, signature, callee, window.
    ///
    /// # Errors
    /// The first failed check; all of them mean `service_token_invalid` to the caller.
    pub fn verify(&self, token: &str, now: Instant) -> Result<ServiceName, TokenError> {
        let parsed = Parsed::parse(token)?;
        let key = self
            .keys
            .get(&parsed.sender, parsed.key_id)
            .ok_or(TokenError::UnknownKey)?;
        verify_mac(key, parsed.signed, &parsed.mac)?;
        ensure_addressed_to(&parsed.receiver, &self.callee)?;
        check_window(parsed.issued, parsed.expires, now)?;
        Ok(parsed.sender)
    }
}

struct Parsed<'a> {
    key_id: KeyId,
    sender: ServiceName,
    receiver: ServiceName,
    issued: i64,
    expires: i64,
    signed: &'a str,
    mac: Vec<u8>,
}

impl<'a> Parsed<'a> {
    fn parse(token: &'a str) -> Result<Self, TokenError> {
        let (signed, mac_hex) = token.rsplit_once('.').ok_or(TokenError::Malformed)?;
        let [version, key_id, sender, receiver, issued, expires] =
            split_fields(signed).ok_or(TokenError::Malformed)?;
        (version == VERSION)
            .then_some(())
            .ok_or(TokenError::Malformed)?;
        Ok(Self {
            key_id: KeyId(key_id.parse().map_err(|_| TokenError::Malformed)?),
            sender: ServiceName::parse(sender).map_err(|_| TokenError::Malformed)?,
            receiver: ServiceName::parse(receiver).map_err(|_| TokenError::Malformed)?,
            issued: issued.parse().map_err(|_| TokenError::Malformed)?,
            expires: expires.parse().map_err(|_| TokenError::Malformed)?,
            signed,
            mac: hex::decode(mac_hex).ok_or(TokenError::Malformed)?,
        })
    }
}

/// Exactly six dot-separated fields, or `None`.
fn split_fields(signed: &str) -> Option<[&str; 6]> {
    let mut parts = signed.split('.');
    let fields = [
        parts.next()?,
        parts.next()?,
        parts.next()?,
        parts.next()?,
        parts.next()?,
        parts.next()?,
    ];
    parts.next().is_none().then_some(fields)
}

fn ensure_addressed_to(receiver: &ServiceName, callee: &ServiceName) -> Result<(), TokenError> {
    (receiver == callee)
        .then_some(())
        .ok_or(TokenError::WrongCallee)
}

fn sign(key: &SigningKey, text: &str) -> Option<Vec<u8>> {
    let mut mac = HmacSha256::new_from_slice(key.bytes()).ok()?;
    mac.update(text.as_bytes());
    Some(mac.finalize().into_bytes().to_vec())
}

// why: `verify_slice` compares in constant time, so the check leaks nothing about the MAC.
fn verify_mac(key: &SigningKey, signed: &str, mac: &[u8]) -> Result<(), TokenError> {
    let mut expected =
        HmacSha256::new_from_slice(key.bytes()).map_err(|_| TokenError::BadSignature)?;
    expected.update(signed.as_bytes());
    expected
        .verify_slice(mac)
        .map_err(|_| TokenError::BadSignature)
}

fn check_window(issued: i64, expires: i64, now: Instant) -> Result<(), TokenError> {
    let lifetime = expires.saturating_sub(issued);
    if u64::try_from(lifetime).map_or(true, |seconds| seconds > MAX_LIFETIME.as_secs()) {
        return Err(TokenError::LifetimeTooLong);
    }
    let seconds_now = now.unix_seconds();
    if seconds_now > expires {
        return Err(TokenError::Expired);
    }
    let skew = i64::try_from(CLOCK_SKEW.as_secs()).unwrap_or(0);
    if seconds_now < issued.saturating_sub(skew) {
        return Err(TokenError::NotYetValid);
    }
    Ok(())
}
