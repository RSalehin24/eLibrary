use thiserror::Error;

/// Why a token or key was rejected. Every verification failure maps to the HTTP code
/// `service_token_invalid`; the variant is for logs and tests, never for the caller.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum TokenError {
    #[error("malformed token")]
    Malformed,
    #[error("unknown signing key")]
    UnknownKey,
    #[error("bad signature")]
    BadSignature,
    #[error("token is for another service")]
    WrongCallee,
    #[error("token expired")]
    Expired,
    #[error("token not valid yet")]
    NotYetValid,
    #[error("token lifetime exceeds the maximum")]
    LifetimeTooLong,
    #[error("invalid service name")]
    InvalidName,
    #[error("signing key too short")]
    KeyTooShort,
}
