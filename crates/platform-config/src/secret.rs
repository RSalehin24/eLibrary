use std::fmt;

/// A value that must never be logged: `Debug` is redacted and there is no `Display`.
#[derive(Clone, PartialEq, Eq)]
pub struct Secret<T>(T);

impl<T> Secret<T> {
    #[must_use]
    pub fn new(value: T) -> Self {
        Self(value)
    }

    /// The only way to read the value; call sites are easy to audit.
    #[must_use]
    pub fn expose(&self) -> &T {
        &self.0
    }
}

impl<T> fmt::Debug for Secret<T> {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("Secret(<redacted>)")
    }
}
