from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.field_errors import normalized_field_errors
from apps.common.permissions import CanManageAccess
from apps.common.validation import reject_unknown_fields

from .policy import require_editable_account
from .queries import managed_account
from .serializers import ManagedGrantSerializer
from .services import create_managed_grant_outcome

MAX_BULK_GRANTS = 100


class ManagedGrantBulkCreateSerializer(serializers.Serializer):
    entries = serializers.ListField(
        child=serializers.DictField(), min_length=1, max_length=MAX_BULK_GRANTS
    )

    def validate(self, attrs):
        reject_unknown_fields(self)
        identifiers = [str(entry.get("id", "")) for entry in attrs["entries"]]
        if len(identifiers) != len(set(identifiers)):
            raise serializers.ValidationError(
                {"entries": "Each permission requires a distinct request identifier."}
            )
        return attrs


class ManagedGrantBulkEntrySerializer(serializers.Serializer):
    index = serializers.IntegerField()
    id = serializers.UUIDField(allow_null=True)
    status = serializers.ChoiceField(
        choices=("created", "existing", "invalid", "conflict", "forbidden", "not_found")
    )
    code = serializers.CharField(allow_blank=True)
    field_errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )
    grant = ManagedGrantSerializer(allow_null=True)


class ManagedGrantBulkResultSerializer(serializers.Serializer):
    entries = ManagedGrantBulkEntrySerializer(many=True)
    created_count = serializers.IntegerField()
    existing_count = serializers.IntegerField()
    rejected_count = serializers.IntegerField()


def request_identifier(values):
    try:
        return UUID(str(values.get("id", "")))
    except (ValueError, TypeError, AttributeError):
        return None


def rejected_entry(error):
    statuses = {400: "invalid", 403: "forbidden", 404: "not_found", 409: "conflict"}
    detail = error.detail
    return {
        "status": statuses[error.status_code],
        "code": error.default_code,
        "field_errors": normalized_field_errors(detail)
        if error.status_code == 400
        else {},
        "grant": None,
    }


def create_entry(actor, identifier, values):
    try:
        grant, created = create_managed_grant_outcome(actor, identifier, values)
        return {
            "status": "created" if created else "existing",
            "code": "",
            "field_errors": {},
            "grant": ManagedGrantSerializer(grant).data,
        }
    except APIException as error:
        if error.status_code not in (400, 403, 404, 409):
            raise
        return rejected_entry(error)


def create_managed_grants(actor, identifier, values):
    require_editable_account(actor, managed_account(identifier))
    serializer = ManagedGrantBulkCreateSerializer(data=values)
    serializer.is_valid(raise_exception=True)
    entries = [
        {
            "index": index,
            "id": request_identifier(entry),
            **create_entry(actor, identifier, entry),
        }
        for index, entry in enumerate(serializer.validated_data["entries"])
    ]
    created = sum(entry["status"] == "created" for entry in entries)
    existing = sum(entry["status"] == "existing" for entry in entries)
    return {
        "entries": entries,
        "created_count": created,
        "existing_count": existing,
        "rejected_count": len(entries) - created - existing,
    }


class ManagedAccountBulkGrantView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageAccess)

    @extend_schema(
        operation_id="managed_account_grants_bulk_create",
        request=ManagedGrantBulkCreateSerializer,
        responses={
            200: ManagedGrantBulkResultSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def post(self, request, identifier):
        return Response(create_managed_grants(request.user, identifier, request.data))
