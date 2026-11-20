//! The slug as it arrives in a path: parsed once at the edge (INV-CAT-005).

const MAX_CHARS: usize = 200;

/// A well-formed slug: 1 to 200 characters, no whitespace and no `/`. Whether the book exists is
/// the store's question.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct SlugParam(String);

impl SlugParam {
    pub(crate) fn parse(text: &str) -> Option<Self> {
        let well_formed = !text.is_empty()
            && text.chars().count() <= MAX_CHARS
            && !text.chars().any(|c| c.is_whitespace() || c == '/');
        well_formed.then(|| Self(text.to_owned()))
    }

    pub(crate) fn as_str(&self) -> &str {
        &self.0
    }
}

#[cfg(test)]
mod tests {
    use super::SlugParam;

    #[test]
    fn accepts_latin_and_bengali_slugs() {
        assert!(SlugParam::parse("a-book-2").is_some());
        assert!(SlugParam::parse("পথের-পাঁচালী").is_some());
    }

    #[test]
    fn refuses_empty_spaced_slashed_and_long_slugs() {
        assert!(SlugParam::parse("").is_none());
        assert!(SlugParam::parse("a b").is_none());
        assert!(SlugParam::parse("a/b").is_none());
        assert!(SlugParam::parse(&"x".repeat(201)).is_none());
        assert!(SlugParam::parse(&"x".repeat(200)).is_some());
    }
}
