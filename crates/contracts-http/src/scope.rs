use serde::{Deserialize, Serialize};
use utoipa::ToSchema;

/// The scope a route declares; every route declares exactly one.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "snake_case")]
#[non_exhaustive]
pub enum Scope {
    Public,
    Browse,
    Preview,
    Read,
    ReadOnce,
    Download,
    Kindle,
    Operate,
    ManageCatalog,
    ManageUsers,
    /// Any signed-in user, own data only.
    Session,
}
