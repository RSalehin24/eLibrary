//! Identifier newtypes shared across services. Generation is the caller's job:
//! this crate only wraps, parses and prints, so it stays pure.

use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// The text is not a valid UUID.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct InvalidId;

impl fmt::Display for InvalidId {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("invalid identifier")
    }
}

impl std::error::Error for InvalidId {}

// why: four identical wrappers; a macro keeps one definition of the rules (DRY).
macro_rules! uuid_id {
    ($(#[$meta:meta])* $name:ident) => {
        $(#[$meta])*
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
        #[serde(transparent)]
        pub struct $name(Uuid);

        impl $name {
            #[must_use]
            pub fn from_uuid(uuid: Uuid) -> Self {
                Self(uuid)
            }

            #[must_use]
            pub fn as_uuid(&self) -> Uuid {
                self.0
            }
        }

        impl fmt::Display for $name {
            fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
                self.0.fmt(formatter)
            }
        }

        impl FromStr for $name {
            type Err = InvalidId;

            fn from_str(text: &str) -> Result<Self, InvalidId> {
                Uuid::parse_str(text).map(Self).map_err(|_| InvalidId)
            }
        }
    };
}

uuid_id!(
    /// A book.
    BookId
);
uuid_id!(
    /// A signed-in user.
    UserId
);
uuid_id!(
    /// One version of a book.
    VersionId
);
uuid_id!(
    /// One section of a book version.
    SectionId
);
