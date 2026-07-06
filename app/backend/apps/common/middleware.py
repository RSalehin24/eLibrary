from django.http import JsonResponse


class RequireTotpSetupMiddleware:
    allowed_api_paths = {
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

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            request.path.startswith("/api/")
            and request.path not in self.allowed_api_paths
            and getattr(user, "is_authenticated", False)
            and getattr(user, "requires_totp_setup", False)
        ):
            return JsonResponse(
                {
                    "detail": "TOTP setup is required for this account before continuing.",
                    "code": "otp_setup_required",
                },
                status=403,
            )
        return self.get_response(request)
