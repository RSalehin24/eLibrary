/// Why access was denied (closed list; the HTTP mapping lives in the service).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum DenyReason {
    NoScope,
    GrantExpired,
    AccountInactive,
    MfaIncomplete,
    BookNotPublished,
    BookDeleted,
    ReadOnceConsumed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Decision {
    Allow,
    Deny(DenyReason),
}

impl Decision {
    #[must_use]
    pub fn is_allowed(self) -> bool {
        self == Self::Allow
    }
}
