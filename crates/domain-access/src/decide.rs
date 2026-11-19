use contracts_http::Scope;
use contracts_ids::TicketId;
use platform_time::Instant;

use crate::{
    AccountStatus, BookFacts, Decision, DenyReason, Grant, ReadOnceStatus, Role, Subject,
    UserFacts, role_scopes,
};

const MANAGEMENT_SCOPES: [Scope; 3] = [Scope::Operate, Scope::ManageCatalog, Scope::ManageUsers];
const BOOK_SCOPES: [Scope; 7] = [
    Scope::Public,
    Scope::Browse,
    Scope::Preview,
    Scope::Read,
    Scope::ReadOnce,
    Scope::Download,
    Scope::Kindle,
];

/// Everything `decide` looks at; no clock read, no I/O.
#[derive(Debug, Clone, Copy)]
pub struct DecisionInput<'a> {
    pub subject: Subject,
    pub scope: Scope,
    pub book: Option<BookFacts>,
    pub grants: &'a [Grant],
    pub now: Instant,
    pub read_once: ReadOnceStatus,
    /// The ticket asking, when the request is a redemption.
    pub ticket: Option<TicketId>,
}

/// Pure and total: every input gives a decision, and nothing matching means Deny (INV-IDN-013).
#[must_use]
pub fn decide(input: &DecisionInput<'_>) -> Decision {
    match input.subject {
        Subject::Anonymous => decide_anonymous(input),
        Subject::User(user) => decide_user(input, user),
    }
}

fn decide_anonymous(input: &DecisionInput<'_>) -> Decision {
    if input.scope != Scope::Public {
        return Decision::Deny(DenyReason::NoScope);
    }
    book_visibility(input.book, false).map_or(Decision::Allow, Decision::Deny)
}

fn decide_user(input: &DecisionInput<'_>, user: UserFacts) -> Decision {
    if user.status != AccountStatus::Active {
        return Decision::Deny(DenyReason::AccountInactive);
    }
    if MANAGEMENT_SCOPES.contains(&input.scope) && !user.mfa_satisfied {
        return Decision::Deny(DenyReason::MfaIncomplete);
    }
    let sees_everything = holds_scope(user.role, input, Scope::ManageCatalog);
    if let Some(reason) = visibility_denial(input, sees_everything) {
        return Decision::Deny(reason);
    }
    entitlement(input, user.role)
}

fn visibility_denial(input: &DecisionInput<'_>, sees_everything: bool) -> Option<DenyReason> {
    if !BOOK_SCOPES.contains(&input.scope) || sees_everything {
        return None;
    }
    book_visibility(input.book, true)
}

/// `None` when the book may be seen; a missing book counts as not published (maps to not found).
fn book_visibility(book: Option<BookFacts>, book_required: bool) -> Option<DenyReason> {
    let Some(facts) = book else {
        return book_required.then_some(DenyReason::BookNotPublished);
    };
    if facts.deleted {
        return Some(DenyReason::BookDeleted);
    }
    (!facts.published).then_some(DenyReason::BookNotPublished)
}

fn entitlement(input: &DecisionInput<'_>, role: Role) -> Decision {
    let open_to_every_active_user = [Scope::Public, Scope::Session].contains(&input.scope);
    if open_to_every_active_user || holds_scope(role, input, input.scope) {
        return read_once_gate(input);
    }
    Decision::Deny(missing_scope_reason(input))
}

fn holds_scope(role: Role, input: &DecisionInput<'_>, scope: Scope) -> bool {
    role_scopes(role).contains(&scope)
        || input
            .grants
            .iter()
            .any(|grant| names_scope(grant, input, scope) && is_live(grant, input.now))
}

/// Is this grant for `scope` and for the requested book (or global)?
fn names_scope(grant: &Grant, input: &DecisionInput<'_>, scope: Scope) -> bool {
    let covers_book = grant.book.is_none() || grant.book == input.book.map(|facts| facts.id);
    grant.scope == scope && covers_book
}

fn is_live(grant: &Grant, now: Instant) -> bool {
    !grant.revoked && grant.expires_at.is_none_or(|expiry| now < expiry)
}

// why: an expired grant that was the only source gives `grant_expired`; a revoked one never does.
fn missing_scope_reason(input: &DecisionInput<'_>) -> DenyReason {
    let had_expired = input
        .grants
        .iter()
        .any(|grant| !grant.revoked && names_scope(grant, input, input.scope));
    if had_expired {
        return DenyReason::GrantExpired;
    }
    DenyReason::NoScope
}

fn read_once_gate(input: &DecisionInput<'_>) -> Decision {
    match (input.scope, input.read_once) {
        (Scope::ReadOnce, ReadOnceStatus::ConsumedBy(used)) if input.ticket != Some(used) => {
            Decision::Deny(DenyReason::ReadOnceConsumed)
        }
        _ => Decision::Allow,
    }
}
