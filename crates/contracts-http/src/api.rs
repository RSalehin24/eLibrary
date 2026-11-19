use utoipa::OpenApi;

use crate::{ErrorBody, ErrorEnvelope, Scope};

/// The schemas every service shares; each service's own document builds on these.
#[derive(OpenApi)]
#[openapi(
    info(title = "eLibrary shared HTTP types", version = "0.1.0"),
    components(schemas(ErrorEnvelope, ErrorBody, Scope))
)]
pub struct CommonApi;
