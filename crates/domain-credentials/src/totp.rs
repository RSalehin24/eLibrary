use std::fmt;

use hmac::{Hmac, KeyInit, Mac};
use platform_time::Instant;
use sha1::Sha1;
use thiserror::Error;

use crate::base32;

pub const TOTP_DIGITS: usize = 6;
pub const TOTP_STEP_SECONDS: i64 = 30;
const MINIMUM_SECRET_BYTES: usize = 16;
const CODE_MODULUS: u32 = 1_000_000;
const DYNAMIC_OFFSET_MASK: u8 = 0x0f;
const HIGH_BIT_MASK: u32 = 0x7fff_ffff;
/// Codes from one step before and after the current one are accepted (clock drift).
const DRIFT_STEPS: [i64; 3] = [-1, 0, 1];

type HmacSha1 = Hmac<Sha1>;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum TotpError {
    #[error("secret is too short or not base32")]
    InvalidSecret,
    #[error("code is wrong")]
    InvalidCode,
    #[error("code was already used or is older than the last accepted step")]
    Replayed,
}

/// A 30-second time step number (unix seconds / 30).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct TotpStep(pub u64);

/// The shared secret; redacted in `Debug`, no `Display`.
#[derive(Clone, PartialEq, Eq)]
pub struct TotpSecret(Vec<u8>);

impl TotpSecret {
    /// # Errors
    /// [`TotpError::InvalidSecret`] below 16 bytes.
    pub fn from_bytes(bytes: Vec<u8>) -> Result<Self, TotpError> {
        (bytes.len() >= MINIMUM_SECRET_BYTES)
            .then_some(Self(bytes))
            .ok_or(TotpError::InvalidSecret)
    }

    /// # Errors
    /// [`TotpError::InvalidSecret`] for bad base32 or a short secret.
    pub fn from_base32(text: &str) -> Result<Self, TotpError> {
        base32::decode(text)
            .ok_or(TotpError::InvalidSecret)
            .and_then(Self::from_bytes)
    }

    /// The form shown at enrolment (QR payload or manual entry).
    #[must_use]
    pub fn to_base32(&self) -> String {
        base32::encode(&self.0)
    }

    /// The code for one step (RFC 4226 dynamic truncation, 6 digits).
    #[must_use]
    pub fn code_for(&self, step: TotpStep) -> u32 {
        let digest = self.mac(step.0);
        let offset = digest
            .last()
            .map_or(0, |byte| usize::from(byte & DYNAMIC_OFFSET_MASK));
        let window: [u8; 4] = digest
            .get(offset..offset + 4)
            .and_then(|bytes| bytes.try_into().ok())
            .unwrap_or_default();
        (u32::from_be_bytes(window) & HIGH_BIT_MASK) % CODE_MODULUS
    }

    fn mac(&self, counter: u64) -> Vec<u8> {
        hmac_sha1(&self.0, counter)
    }
}

fn hmac_sha1(key: &[u8], counter: u64) -> Vec<u8> {
    let Ok(mut mac) = HmacSha1::new_from_slice(key) else {
        return Vec::new();
    };
    mac.update(&counter.to_be_bytes());
    mac.finalize().into_bytes().to_vec()
}

impl fmt::Debug for TotpSecret {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("TotpSecret(<redacted>)")
    }
}

/// One sign-in attempt: what was typed, when, and the newest step already accepted.
#[derive(Debug, Clone, Copy)]
pub struct Attempt<'a> {
    pub code: &'a str,
    pub now: Instant,
    pub last_accepted: Option<TotpStep>,
}

/// Checks a typed code. On success returns the accepted step, which the caller stores as the new
/// last accepted step in the same transaction: steps only increase (INV-IDN-005), so a captured
/// code cannot be replayed.
///
/// # Errors
/// [`TotpError::InvalidCode`] for a malformed or wrong code; [`TotpError::Replayed`] when the code
/// is valid but its step is not newer than the last accepted one.
pub fn verify_code(secret: &TotpSecret, attempt: Attempt<'_>) -> Result<TotpStep, TotpError> {
    let typed = parse_code(attempt.code).ok_or(TotpError::InvalidCode)?;
    let current = attempt.now.unix_seconds().div_euclid(TOTP_STEP_SECONDS);
    let matching: Vec<TotpStep> = DRIFT_STEPS
        .iter()
        .filter_map(|drift| u64::try_from(current + drift).ok())
        .map(TotpStep)
        .filter(|step| secret.code_for(*step) == typed)
        .collect();
    let newest = matching
        .iter()
        .max()
        .copied()
        .ok_or(TotpError::InvalidCode)?;
    let is_new = attempt.last_accepted.is_none_or(|last| newest > last);
    is_new.then_some(newest).ok_or(TotpError::Replayed)
}

fn parse_code(code: &str) -> Option<u32> {
    let well_formed = code.len() == TOTP_DIGITS && code.bytes().all(|b| b.is_ascii_digit());
    well_formed.then(|| code.parse().ok()).flatten()
}
