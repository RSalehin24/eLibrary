use std::fmt;

use crate::TokenError;

const MAX_LENGTH: usize = 32;

/// A service name: lowercase letters, digits and hyphens, starting with a letter. The
/// restricted alphabet keeps `.` free as the token field separator.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ServiceName(String);

impl ServiceName {
    /// # Errors
    /// [`TokenError::InvalidName`] when the text is empty, too long or has other characters.
    pub fn parse(text: &str) -> Result<Self, TokenError> {
        is_valid(text)
            .then(|| Self(text.to_owned()))
            .ok_or(TokenError::InvalidName)
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for ServiceName {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

fn is_valid(text: &str) -> bool {
    let starts_with_letter = text.chars().next().is_some_and(|c| c.is_ascii_lowercase());
    let allowed = text
        .chars()
        .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-');
    starts_with_letter && allowed && text.len() <= MAX_LENGTH
}
