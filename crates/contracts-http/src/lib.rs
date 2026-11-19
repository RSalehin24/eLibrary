//! Wire types shared by every HTTP surface: error envelope, scopes, pagination.
//! Rules: `planning/07-contracts/http/README.md` and `planning/07-contracts/error-catalog.md`.

mod error;
mod error_code;
mod page;
mod scope;

pub use error::{ErrorBody, ErrorEnvelope};
pub use error_code::{CommonErrorCode, ErrorClass};
pub use page::Page;
pub use scope::Scope;
