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

impl Scope {
    pub const ALL: [Self; 11] = [
        Self::Public,
        Self::Browse,
        Self::Preview,
        Self::Read,
        Self::ReadOnce,
        Self::Download,
        Self::Kindle,
        Self::Operate,
        Self::ManageCatalog,
        Self::ManageUsers,
        Self::Session,
    ];

    /// The wire name; an exhaustive match, so a new scope cannot be added without a name.
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Public => "public",
            Self::Browse => "browse",
            Self::Preview => "preview",
            Self::Read => "read",
            Self::ReadOnce => "read_once",
            Self::Download => "download",
            Self::Kindle => "kindle",
            Self::Operate => "operate",
            Self::ManageCatalog => "manage_catalog",
            Self::ManageUsers => "manage_users",
            Self::Session => "session",
        }
    }
}
