use std::cmp::Ordering;

use icu_collator::options::CollatorOptions;
use icu_collator::{Collator, CollatorBorrowed, CollatorPreferences};
use icu_locale_core::locale;

/// The compiled collation data could not be loaded.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CollationUnavailable;

impl std::fmt::Display for CollationUnavailable {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("bn collation data unavailable")
    }
}

impl std::error::Error for CollationUnavailable {}

/// Bytes whose lexicographic order equals CLDR `bn` order; stored as `bytea` for DB-side sorting.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SortKey(Vec<u8>);

impl SortKey {
    #[must_use]
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }
}

/// The one comparator shared by catalog listing and search.
pub struct BengaliCollator(CollatorBorrowed<'static>);

impl BengaliCollator {
    /// # Errors
    /// Returns [`CollationUnavailable`] if the compiled data cannot be loaded.
    pub fn new() -> Result<Self, CollationUnavailable> {
        let preferences = CollatorPreferences::from(locale!("bn"));
        Collator::try_new(preferences, CollatorOptions::default())
            .map(Self)
            .map_err(|_| CollationUnavailable)
    }

    #[must_use]
    pub fn compare(&self, left: &str, right: &str) -> Ordering {
        self.0.compare(left, right)
    }

    #[must_use]
    pub fn sort_key(&self, text: &str) -> SortKey {
        let mut bytes = Vec::new();
        let Ok(()) = self.0.write_sort_key_to(text, &mut bytes);
        SortKey(bytes)
    }
}
