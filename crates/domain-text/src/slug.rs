use crate::keys::ExactKey;

/// URL segment for a book: key text with words joined by hyphens, Bengali letters kept.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Slug(String);

impl Slug {
    /// `None` when the text has no letters or digits to build a slug from.
    #[must_use]
    pub fn from_title(title: &str) -> Option<Self> {
        let key = ExactKey::new(title);
        let slug = key.as_str().replace(' ', "-");
        (!slug.is_empty()).then_some(Self(slug))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}
