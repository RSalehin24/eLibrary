from http import HTTPStatus

from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from apps.common.field_errors import normalized_field_errors
from apps.common.http import protect_private_response

ERROR_CODES: dict[int, str] = {
    HTTPStatus.NOT_FOUND: "not_found",
    HTTPStatus.FORBIDDEN: "permission_denied",
}


class VersionedAPIView(APIView):
    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        detail = response.data
        response.data = {
            "code": getattr(
                exc,
                "default_code",
                ERROR_CODES.get(response.status_code, "request_failed"),
            ),
            "detail": "Check the supplied fields."
            if isinstance(exc, ValidationError)
            else detail.get("detail", "Request failed."),
            "field_errors": normalized_field_errors(detail)
            if isinstance(exc, ValidationError)
            else {},
        }
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if response.status_code >= HTTPStatus.BAD_REQUEST and isinstance(
            response.data, dict
        ):
            response.data.setdefault("field_errors", {})
        return protect_private_response(response)
