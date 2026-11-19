use std::fmt;

use argon2::{Argon2, PasswordHasher, PasswordVerifier};
use thiserror::Error;

/// Documented policy (provisional, owner may change): length counted in characters.
pub const PASSWORD_MIN_CHARS: usize = 12;
pub const PASSWORD_MAX_CHARS: usize = 128;
/// Argon2 needs at least 8 salt bytes; the caller supplies 16 random bytes.
pub const SALT_BYTES: usize = 16;

// why: a small built-in deny list of the most common choices; compared case-insensitively.
const DENY_LIST: [&str; 12] = [
    "password1234",
    "123456789012",
    "qwertyuiop12",
    "iloveyou1234",
    "administrator",
    "letmein12345",
    "welcome12345",
    "changeme1234",
    "passwordpassword",
    "111111111111",
    "abcdefghijkl",
    "bangladesh123",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum PasswordError {
    #[error("password is shorter than {PASSWORD_MIN_CHARS} characters")]
    TooShort,
    #[error("password is longer than {PASSWORD_MAX_CHARS} characters")]
    TooLong,
    #[error("password is on the deny list")]
    TooCommon,
    #[error("password could not be hashed")]
    HashFailed,
}

/// A password that passed the policy. No `Debug` content, no `Display`, not `Clone`.
pub struct Password(String);

impl Password {
    /// # Errors
    /// The first policy rule the text breaks.
    pub fn parse(text: &str) -> Result<Self, PasswordError> {
        let length = text.chars().count();
        let lowered = text.to_lowercase();
        let verdict = match length {
            0..PASSWORD_MIN_CHARS => Err(PasswordError::TooShort),
            PASSWORD_MIN_CHARS..=PASSWORD_MAX_CHARS => Ok(()),
            _ => Err(PasswordError::TooLong),
        };
        verdict.and_then(|()| not_denied(&lowered))?;
        Ok(Self(text.to_owned()))
    }
}

fn not_denied(lowered: &str) -> Result<(), PasswordError> {
    let denied = DENY_LIST.contains(&lowered);
    (!denied).then_some(()).ok_or(PasswordError::TooCommon)
}

impl fmt::Debug for Password {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("Password(<redacted>)")
    }
}

/// A stored Argon2id hash in PHC string form (algorithm, parameters and salt included).
#[derive(Clone, PartialEq, Eq)]
pub struct PasswordHash(String);

impl PasswordHash {
    /// Hashes with the library's default Argon2id parameters; the salt comes from the caller
    /// (the service's random source), which keeps this crate pure.
    ///
    /// # Errors
    /// [`PasswordError::HashFailed`] if hashing itself fails.
    pub fn create(password: &Password, salt: &[u8; SALT_BYTES]) -> Result<Self, PasswordError> {
        Argon2::default()
            .hash_password_with_salt(password.0.as_bytes(), salt)
            .map(|hash| Self(hash.to_string()))
            .map_err(|_| PasswordError::HashFailed)
    }

    /// Reads a stored hash; `None` when the text is not a PHC string.
    #[must_use]
    pub fn from_stored(text: &str) -> Option<Self> {
        argon2::password_hash::phc::PasswordHash::new(text).ok()?;
        Some(Self(text.to_owned()))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// Checks any attempt (sign-in must not apply the creation policy). Constant time inside
    /// the library; a wrong password and a malformed hash both give `false`.
    #[must_use]
    pub fn verify(&self, attempt: &str) -> bool {
        Argon2::default()
            .verify_password(attempt.as_bytes(), self.0.as_str())
            .is_ok()
    }
}

impl fmt::Debug for PasswordHash {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("PasswordHash(<redacted>)")
    }
}
