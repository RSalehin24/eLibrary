use serde::{Deserialize, Serialize};
use utoipa::ToSchema;

/// Keyset page: pass `next` back as `?after=`; `None` means the last page.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, ToSchema)]
pub struct Page<T> {
    pub items: Vec<T>,
    pub next: Option<String>,
}
