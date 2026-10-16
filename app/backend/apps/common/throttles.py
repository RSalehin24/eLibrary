from redis.exceptions import RedisError
from rest_framework.exceptions import APIException
from rest_framework.throttling import (
    AnonRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)


class RateLimitsUnavailable(APIException):
    status_code = 503
    default_code = "rate_limits_unavailable"
    default_detail = "Request limits are temporarily unavailable. Try again later."


class CacheAvailableThrottle(SimpleRateThrottle):
    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except RedisError:
            raise RateLimitsUnavailable() from None


class LoginRateThrottle(CacheAvailableThrottle, AnonRateThrottle):
    scope = "login"


class RegisterRateThrottle(CacheAvailableThrottle, AnonRateThrottle):
    scope = "register"


class PasswordResetRateThrottle(CacheAvailableThrottle, AnonRateThrottle):
    scope = "password_reset"


class PasswordLinkRateThrottle(CacheAvailableThrottle, AnonRateThrottle):
    scope = "password_link"


class SubmissionRateThrottle(CacheAvailableThrottle, UserRateThrottle):
    scope = "submission"
