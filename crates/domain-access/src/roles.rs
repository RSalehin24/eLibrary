use contracts_http::Scope;

/// The account roles (closed). No role holds every scope; `download` and `read_once` are
/// never part of a role and exist only as grants.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Role {
    Reader,
    Operator,
    Admin,
}

// why: the reader defaults are configuration (D-30); until the config exists they are fixed here.
const READER_SCOPES: [Scope; 4] = [Scope::Browse, Scope::Preview, Scope::Read, Scope::Kindle];
const OPERATOR_SCOPES: [Scope; 6] = [
    Scope::Browse,
    Scope::Preview,
    Scope::Read,
    Scope::Kindle,
    Scope::Operate,
    Scope::ManageCatalog,
];
const ADMIN_SCOPES: [Scope; 6] = [
    Scope::Browse,
    Scope::Preview,
    Scope::Read,
    Scope::Kindle,
    Scope::ManageUsers,
    Scope::ManageCatalog,
];

/// Scopes a role grants by itself (D-45).
#[must_use]
pub fn role_scopes(role: Role) -> &'static [Scope] {
    match role {
        Role::Reader => &READER_SCOPES,
        Role::Operator => &OPERATOR_SCOPES,
        Role::Admin => &ADMIN_SCOPES,
    }
}
