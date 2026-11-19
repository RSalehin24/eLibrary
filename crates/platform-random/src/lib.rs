//! The only way services get random bytes: inject a [`RandomSource`]. Production uses the
//! operating system; tests use a deterministic sequence.

use std::fmt::Write;
use std::sync::atomic::{AtomicU8, Ordering};

use thiserror::Error;

/// The operating system could not provide randomness.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[error("no randomness available")]
pub struct RandomError;

pub trait RandomSource {
    /// # Errors
    /// [`RandomError`] when no randomness can be produced.
    fn fill(&self, buffer: &mut [u8]) -> Result<(), RandomError>;
}

/// Operating-system randomness (`getrandom`).
#[derive(Debug, Clone, Copy, Default)]
pub struct OsRandom;

impl RandomSource for OsRandom {
    fn fill(&self, buffer: &mut [u8]) -> Result<(), RandomError> {
        getrandom::fill(buffer).map_err(|_| RandomError)
    }
}

/// Deterministic bytes for tests: each byte is one more than the last (wrapping).
#[derive(Debug, Default)]
pub struct SequenceRandom(AtomicU8);

impl RandomSource for SequenceRandom {
    fn fill(&self, buffer: &mut [u8]) -> Result<(), RandomError> {
        fill_sequence(&self.0, buffer);
        Ok(())
    }
}

/// `length` random bytes as lowercase hex (tokens, nonces).
///
/// # Errors
/// [`RandomError`] when the source fails.
pub fn random_hex(source: &impl RandomSource, length: usize) -> Result<String, RandomError> {
    let mut bytes = vec![0u8; length];
    source.fill(&mut bytes)?;
    Ok(to_hex(&bytes))
}

/// Lowercase hex of `bytes`.
#[must_use]
pub fn to_hex(bytes: &[u8]) -> String {
    let mut text = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        let _ = write!(text, "{byte:02x}");
    }
    text
}

fn fill_sequence(counter: &AtomicU8, buffer: &mut [u8]) {
    for byte in buffer {
        *byte = counter.fetch_add(1, Ordering::Relaxed);
    }
}

const VERSION_7: u8 = 0x70;
const VERSION_MASK: u8 = 0x0f;
const VARIANT_RFC: u8 = 0x80;
const VARIANT_MASK: u8 = 0x3f;
const TIMESTAMP_BYTES: usize = 6;
const UUID_BYTES: usize = 16;

/// A `UUIDv7` (RFC 9562): 48 bits of unix milliseconds, then random bits, so ids sort by creation.
///
/// # Errors
/// [`RandomError`] when the source fails.
pub fn uuid_v7(unix_millis: u64, source: &impl RandomSource) -> Result<uuid::Uuid, RandomError> {
    let mut bytes = [0u8; UUID_BYTES];
    source.fill(&mut bytes)?;
    let millis = unix_millis.to_be_bytes();
    bytes
        .iter_mut()
        .zip(millis.iter().skip(millis.len() - TIMESTAMP_BYTES))
        .for_each(|(slot, byte)| *slot = *byte);
    set_version_and_variant(&mut bytes);
    Ok(uuid::Uuid::from_bytes(bytes))
}

fn set_version_and_variant(bytes: &mut [u8; UUID_BYTES]) {
    let (version_at, variant_at) = (TIMESTAMP_BYTES, TIMESTAMP_BYTES + 2);
    if let Some(byte) = bytes.get_mut(version_at) {
        *byte = (*byte & VERSION_MASK) | VERSION_7;
    }
    if let Some(byte) = bytes.get_mut(variant_at) {
        *byte = (*byte & VARIANT_MASK) | VARIANT_RFC;
    }
}
