use std::collections::BTreeMap;

use platform_config::Secret;

use crate::{ServiceName, TokenError};

const MINIMUM_KEY_BYTES: usize = 32;

/// Identifies one key of a service so keys can rotate with an overlap.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct KeyId(pub u32);

/// HMAC key bytes; redacted in `Debug`.
#[derive(Clone, PartialEq, Eq)]
pub struct SigningKey(Secret<Vec<u8>>);

impl SigningKey {
    /// # Errors
    /// [`TokenError::KeyTooShort`] below 32 bytes.
    pub fn new(bytes: Vec<u8>) -> Result<Self, TokenError> {
        let long_enough = bytes.len() >= MINIMUM_KEY_BYTES;
        long_enough
            .then(|| Self(Secret::new(bytes)))
            .ok_or(TokenError::KeyTooShort)
    }

    /// Reads the key from its secret file text: hex digits (64 for 32 bytes).
    ///
    /// # Errors
    /// [`TokenError::KeyTooShort`] for text that is not hex or decodes below 32 bytes.
    pub fn from_hex(text: &str) -> Result<Self, TokenError> {
        let bytes = crate::hex::decode(text.trim()).ok_or(TokenError::KeyTooShort)?;
        Self::new(bytes)
    }

    pub(crate) fn bytes(&self) -> &[u8] {
        self.0.expose()
    }
}

impl std::fmt::Debug for SigningKey {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("SigningKey(<redacted>)")
    }
}

/// Whose key it is: a service and which of its (rotating) keys.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct KeyOwner {
    pub service: ServiceName,
    pub id: KeyId,
}

/// The keys a verifier trusts, per caller and key id.
#[derive(Debug, Clone, Default)]
pub struct KeyRing(BTreeMap<KeyOwner, SigningKey>);

impl KeyRing {
    #[must_use]
    pub fn with(mut self, owner: KeyOwner, key: SigningKey) -> Self {
        self.0.insert(owner, key);
        self
    }

    pub(crate) fn get(&self, caller: &ServiceName, key_id: KeyId) -> Option<&SigningKey> {
        self.0.get(&KeyOwner {
            service: caller.clone(),
            id: key_id,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::SigningKey;
    use crate::TokenError;

    #[test]
    fn reads_a_64_digit_hex_secret_file() {
        let text = format!("{}\n", "ab".repeat(32));
        assert!(SigningKey::from_hex(&text).is_ok());
    }

    #[test]
    fn refuses_short_or_non_hex_text() {
        assert_eq!(
            SigningKey::from_hex("abcd").err(),
            Some(TokenError::KeyTooShort)
        );
        assert_eq!(
            SigningKey::from_hex(&"zz".repeat(32)).err(),
            Some(TokenError::KeyTooShort)
        );
    }
}
