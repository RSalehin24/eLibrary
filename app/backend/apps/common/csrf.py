from django.http import JsonResponse
from django.views.csrf import csrf_failure as django_csrf_failure

from apps.common.http import protect_private_response


def csrf_failure(request, reason="", template_name="403_csrf.html"):
    if not request.path.startswith("/api/v1/"):
        return django_csrf_failure(request, reason, template_name)
    return protect_private_response(JsonResponse(
        {"code": "csrf_failed", "detail": "CSRF verification failed.", "field_errors": {}},
        status=403,
    ))
