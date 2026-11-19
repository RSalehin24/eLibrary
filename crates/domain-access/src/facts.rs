use contracts_http::Scope;
use contracts_ids::{BookId, TicketId};
use platform_time::Instant;

use crate::Role;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AccountStatus {
    Invited,
    Active,
    Suspended,
    Disabled,
}

/// What `decide` needs to know about a signed-in user (no shelf, ownership or import data:
/// INV-IDN-015 is enforced by this type having no room for them).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct UserFacts {
    pub status: AccountStatus,
    pub role: Role,
    /// True when the account does not require TOTP or this session completed it.
    pub mfa_satisfied: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Subject {
    Anonymous,
    User(UserFacts),
}

/// An explicit grant of one scope, for one book or globally.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Grant {
    pub scope: Scope,
    /// `None` is a global grant.
    pub book: Option<BookId>,
    pub expires_at: Option<Instant>,
    pub revoked: bool,
}

/// Facts about the requested book, supplied by the caller (catalog owns them).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BookFacts {
    pub id: BookId,
    pub published: bool,
    pub deleted: bool,
}

/// Whether the one read-once use of this user and book was already spent.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReadOnceStatus {
    Unused,
    ConsumedBy(TicketId),
}
