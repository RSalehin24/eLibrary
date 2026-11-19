//! Text normalization shared by ingestion, catalog and reader.
//!
//! Spec: `planning/04-architecture/cross-cutting/text-and-time.md`.

mod collation;
mod display;
mod fuzzy;
mod keys;
mod slug;

pub use collation::{BengaliCollator, CollationUnavailable, SortKey};
pub use display::DisplayText;
pub use fuzzy::FuzzyKey;
pub use keys::ExactKey;
pub use slug::Slug;

/// Bump on any change to key output; consumers reindex when it changes.
pub const NORMALIZER_VERSION: u32 = 1;
