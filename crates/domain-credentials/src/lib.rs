//! Password hashing (Argon2id) and TOTP (RFC 6238): pure, with salts and time injected.
//! Spec: REQ-IDN-003 to REQ-IDN-005 in `planning/02-requirements/idn-identity.md`.

mod base32;
mod email;
mod password;
mod totp;

pub use email::{Email, EmailError, KindleEmail, KindleEmailError};
pub use password::{
    PASSWORD_MAX_CHARS, PASSWORD_MIN_CHARS, Password, PasswordError, PasswordHash, SALT_BYTES,
};
pub use totp::{
    Attempt, TOTP_DIGITS, TOTP_STEP_SECONDS, TotpError, TotpSecret, TotpStep, verify_code,
};
