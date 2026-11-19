/// Whether retrying can help; never decided from the message text.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorClass {
    Retryable,
    Permanent,
}

/// Codes every service can return (401/403 and the Common section of the catalog).
/// Service-specific codes live in each service's contract crate.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[non_exhaustive]
pub enum CommonErrorCode {
    Unauthenticated,
    Forbidden,
    MfaRequired,
    CsrfInvalid,
    ServiceTokenInvalid,
    ValidationFailed,
    BodyTooLarge,
    RateLimited,
    NotFound,
    Conflict,
    StaleRevision,
    IdempotencyConflict,
    InvalidTransition,
    LimitExceeded,
    PeerUnavailable,
    QueueUnavailable,
    Timeout,
    InternalError,
    RouteScopeMissing,
}

impl CommonErrorCode {
    pub const ALL: [Self; 19] = [
        Self::Unauthenticated,
        Self::Forbidden,
        Self::MfaRequired,
        Self::CsrfInvalid,
        Self::ServiceTokenInvalid,
        Self::ValidationFailed,
        Self::BodyTooLarge,
        Self::RateLimited,
        Self::NotFound,
        Self::Conflict,
        Self::StaleRevision,
        Self::IdempotencyConflict,
        Self::InvalidTransition,
        Self::LimitExceeded,
        Self::PeerUnavailable,
        Self::QueueUnavailable,
        Self::Timeout,
        Self::InternalError,
        Self::RouteScopeMissing,
    ];

    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Unauthenticated => "unauthenticated",
            Self::Forbidden => "forbidden",
            Self::MfaRequired => "mfa_required",
            Self::CsrfInvalid => "csrf_invalid",
            Self::ServiceTokenInvalid => "service_token_invalid",
            Self::ValidationFailed => "validation_failed",
            Self::BodyTooLarge => "body_too_large",
            Self::RateLimited => "rate_limited",
            Self::NotFound => "not_found",
            Self::Conflict => "conflict",
            Self::StaleRevision => "stale_revision",
            Self::IdempotencyConflict => "idempotency_conflict",
            Self::InvalidTransition => "invalid_transition",
            Self::LimitExceeded => "limit_exceeded",
            Self::PeerUnavailable => "peer_unavailable",
            Self::QueueUnavailable => "queue_unavailable",
            Self::Timeout => "timeout",
            Self::InternalError => "internal_error",
            Self::RouteScopeMissing => "route_scope_missing",
        }
    }

    /// HTTP status; one exhaustive function so a new code cannot forget its status.
    #[must_use]
    pub fn http_status(self) -> u16 {
        match self {
            Self::Unauthenticated | Self::ServiceTokenInvalid => 401,
            Self::Forbidden | Self::MfaRequired | Self::CsrfInvalid => 403,
            Self::NotFound => 404,
            Self::Conflict | Self::InvalidTransition => 409,
            Self::StaleRevision => 412,
            Self::BodyTooLarge => 413,
            Self::ValidationFailed | Self::IdempotencyConflict | Self::LimitExceeded => 422,
            Self::RateLimited => 429,
            Self::InternalError | Self::RouteScopeMissing => 500,
            Self::PeerUnavailable | Self::QueueUnavailable => 503,
            Self::Timeout => 504,
        }
    }

    #[must_use]
    pub fn class(self) -> ErrorClass {
        class_of(self)
    }
}

fn class_of(code: CommonErrorCode) -> ErrorClass {
    use CommonErrorCode as Code;
    match code {
        Code::RateLimited | Code::PeerUnavailable | Code::QueueUnavailable | Code::Timeout => {
            ErrorClass::Retryable
        }
        Code::Unauthenticated
        | Code::Forbidden
        | Code::MfaRequired
        | Code::CsrfInvalid
        | Code::ServiceTokenInvalid
        | Code::ValidationFailed
        | Code::BodyTooLarge
        | Code::NotFound
        | Code::Conflict
        | Code::StaleRevision
        | Code::IdempotencyConflict
        | Code::InvalidTransition
        | Code::LimitExceeded
        | Code::InternalError
        | Code::RouteScopeMissing => ErrorClass::Permanent,
    }
}
