//! Internal service tokens (`Authorization: Service <token>`): the caller names itself and the
//! callee, signs with its own key, and the token lives at most 60 s.
//! Spec: `planning/04-architecture/cross-cutting/service-auth.md`.

mod error;
mod hex;
mod key;
mod name;
mod token;

pub use error::TokenError;
pub use key::{KeyId, KeyOwner, KeyRing, SigningKey};
pub use name::ServiceName;
pub use token::{IssueRequest, MAX_LIFETIME, Token, TokenIssuer, Verifier, bearer_token};
