//! Encryption of TOTP secrets at rest (XChaCha20-Poly1305). The stored value is
//! `nonce || ciphertext`; the nonce is injected so tests are deterministic, and the user id is
//! bound as associated data so a secret cannot be moved to another account's row.

use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{Key, XChaCha20Poly1305, XNonce};
use platform_random::{RandomError, RandomSource};
use thiserror::Error;
use uuid::Uuid;

pub const KEY_BYTES: usize = 32;
const NONCE_BYTES: usize = 24;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
pub enum VaultError {
    #[error("the vault key must be exactly {KEY_BYTES} bytes")]
    BadKey,
    #[error("randomness: {0}")]
    Random(#[from] RandomError),
    #[error("the sealed value is corrupt or was sealed for another account")]
    Unsealed,
}

/// The key from the secret file; no `Debug` or `Display`.
pub struct VaultKey(Key);

impl VaultKey {
    /// # Errors
    /// [`VaultError::BadKey`] unless the bytes are exactly 32.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self, VaultError> {
        let array: [u8; KEY_BYTES] = bytes.try_into().map_err(|_| VaultError::BadKey)?;
        Ok(Self(Key::from(array)))
    }
}

impl VaultKey {
    /// The key as it is kept in the secret file: 64 hex characters.
    ///
    /// # Errors
    /// [`VaultError::BadKey`] for anything but 64 hex characters.
    pub fn from_hex(text: &str) -> Result<Self, VaultError> {
        let bytes = decode_hex(text).ok_or(VaultError::BadKey)?;
        Self::from_bytes(&bytes)
    }
}

fn decode_hex(text: &str) -> Option<Vec<u8>> {
    let digits = text.as_bytes();
    (digits.len() == KEY_BYTES * 2).then_some(())?;
    digits
        .chunks(2)
        .map(|pair| {
            let pair = std::str::from_utf8(pair).ok()?;
            u8::from_str_radix(pair, 16).ok()
        })
        .collect()
}

/// What is sealed and whose it is.
#[derive(Clone, Copy)]
pub struct Plain<'a> {
    pub owner: Uuid,
    pub bytes: &'a [u8],
}

/// # Errors
/// Randomness or encryption failure.
pub fn seal(
    key: &VaultKey,
    plain: Plain<'_>,
    random: &impl RandomSource,
) -> Result<Vec<u8>, VaultError> {
    let mut nonce = [0_u8; NONCE_BYTES];
    random.fill(&mut nonce)?;
    let payload = Payload {
        msg: plain.bytes,
        aad: plain.owner.as_bytes(),
    };
    let sealed = XChaCha20Poly1305::new(&key.0)
        .encrypt(&XNonce::from(nonce), payload)
        .map_err(|_| VaultError::Unsealed)?;
    Ok([nonce.as_slice(), &sealed].concat())
}

/// # Errors
/// [`VaultError::Unsealed`] for a wrong key, a tampered value or another owner.
pub fn open(key: &VaultKey, owner: Uuid, stored: &[u8]) -> Result<Vec<u8>, VaultError> {
    let (nonce, sealed) = stored
        .split_at_checked(NONCE_BYTES)
        .ok_or(VaultError::Unsealed)?;
    let nonce: [u8; NONCE_BYTES] = nonce.try_into().map_err(|_| VaultError::Unsealed)?;
    let payload = Payload {
        msg: sealed,
        aad: owner.as_bytes(),
    };
    XChaCha20Poly1305::new(&key.0)
        .decrypt(&XNonce::from(nonce), payload)
        .map_err(|_| VaultError::Unsealed)
}

#[cfg(test)]
mod tests {
    use platform_random::SequenceRandom;

    use super::*;

    type Failure = Box<dyn std::error::Error>;

    fn plain(owner: Uuid, bytes: &[u8]) -> Plain<'_> {
        Plain { owner, bytes }
    }

    fn key(byte: u8) -> Result<VaultKey, Failure> {
        Ok(VaultKey::from_bytes(&[byte; KEY_BYTES])?)
    }

    #[test]
    fn a_sealed_secret_opens_for_its_owner() -> Result<(), Failure> {
        let owner = Uuid::from_u128(1);
        let sealed = seal(
            &key(1)?,
            plain(owner, b"JBSWY3DPEHPK3PXP"),
            &SequenceRandom::default(),
        )?;
        assert_eq!(open(&key(1)?, owner, &sealed)?, b"JBSWY3DPEHPK3PXP");
        Ok(())
    }

    #[test]
    fn another_key_another_owner_or_a_flipped_byte_does_not_open() -> Result<(), Failure> {
        let owner = Uuid::from_u128(1);
        let mut sealed = seal(
            &key(1)?,
            plain(owner, b"secret"),
            &SequenceRandom::default(),
        )?;
        assert_eq!(open(&key(2)?, owner, &sealed), Err(VaultError::Unsealed));
        assert_eq!(
            open(&key(1)?, Uuid::from_u128(2), &sealed),
            Err(VaultError::Unsealed)
        );
        let flipped = sealed.last_mut().ok_or("empty")?;
        *flipped ^= 1;
        assert_eq!(open(&key(1)?, owner, &sealed), Err(VaultError::Unsealed));
        Ok(())
    }

    #[test]
    fn short_input_and_short_keys_are_rejected() -> Result<(), Failure> {
        assert_eq!(
            open(&key(1)?, Uuid::nil(), &[0; 5]),
            Err(VaultError::Unsealed)
        );
        assert!(VaultKey::from_bytes(&[0; 16]).is_err());
        assert!(VaultKey::from_hex(&"ab".repeat(32)).is_ok());
        assert!(VaultKey::from_hex(&"zz".repeat(32)).is_err());
        assert!(VaultKey::from_hex("abcd").is_err());
        Ok(())
    }
}
