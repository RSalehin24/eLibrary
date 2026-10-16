from django.http import JsonResponse

from apps.common.http import protect_private_response


class RequireTotpSetupMiddleware:
    allowed_api_paths = frozenset(
        {
            "/api/auth/session/",
            "/api/auth/demo-login/",
            "/api/auth/logout/",
            "/api/auth/profile/",
            "/api/auth/2fa/status/",
            "/api/auth/2fa/setup/",
            "/api/auth/2fa/confirm/",
            "/api/auth/2fa/cancel/",
            "/api/auth/2fa/disable/",
            "/api/csrf/",
        }
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        api_path = request.path.replace("/api/v1/", "/api/", 1)
        public_metadata_read = request.method in {
            "GET",
            "HEAD",
            "OPTIONS",
        } and request.path.startswith("/api/v1/catalog/")
        if (
            request.path.startswith("/api/")
            and api_path not in self.allowed_api_paths
            and not public_metadata_read
            and getattr(user, "is_authenticated", False)
            and getattr(user, "requires_totp_setup", False)
        ):
            response_data: dict[str, object] = {
                "detail": "TOTP setup is required for this account before continuing.",
                "code": "otp_setup_required",
            }
            if request.path.startswith("/api/v1/"):
                response_data["field_errors"] = {}
                return protect_private_response(JsonResponse(response_data, status=403))
            return JsonResponse(response_data, status=403)
        return self.get_response(request)
