use unicode_normalization::UnicodeNormalization;

/// Text for storage and display: NFC, otherwise untouched (ZWJ/ZWNJ kept).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct DisplayText(String);

impl DisplayText {
    #[must_use]
    pub fn new(raw: &str) -> Self {
        Self(raw.nfc().collect())
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}
