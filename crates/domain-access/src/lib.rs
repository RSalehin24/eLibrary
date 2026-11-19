//! Who may do what: the pure, total `decide` function of identity (deny by default).
//! Spec: `planning/05-services/identity/domain-model.md`; model: `formal-models/alloy/access.als`.

mod decide;
mod facts;
mod roles;
mod verdict;

pub use decide::{DecisionInput, decide};
pub use facts::{AccountStatus, BookFacts, Grant, ReadOnceStatus, Subject, UserFacts};
pub use roles::{Role, role_scopes};
pub use verdict::{Decision, DenyReason};
