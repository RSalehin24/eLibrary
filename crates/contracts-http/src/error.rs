use serde::{Deserialize, Serialize};
use utoipa::ToSchema;

use crate::CommonErrorCode;

/// The one error shape on every route: `{ "error": { code, message, request_id, details? } }`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, ToSchema)]
pub struct ErrorEnvelope {
    pub error: ErrorBody,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, ToSchema)]
pub struct ErrorBody {
    /// Stable machine code from the error catalog.
    pub code: String,
    /// Safe to display: never secrets, SQL, stack traces or internal ids.
    pub message: String,
    pub request_id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub details: Option<serde_json::Value>,
}

impl ErrorEnvelope {
    #[must_use]
    pub fn new(code: CommonErrorCode, message: &str, request_id: &str) -> Self {
        Self {
            error: ErrorBody {
                code: code.as_str().to_owned(),
                message: message.to_owned(),
                request_id: request_id.to_owned(),
                details: None,
            },
        }
    }
}
