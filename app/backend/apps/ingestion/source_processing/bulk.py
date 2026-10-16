from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.field_errors import normalized_field_errors
from apps.common.permissions import CanManageProcessing
from apps.common.validation import reject_unknown_fields, reject_unknown_input

from .api import SourceProcessingCommandSerializer
from .commands import request_source_processing


class SourceSelectionSerializer(SourceProcessingCommandSerializer):
    source_id = serializers.UUIDField()

    def to_internal_value(self, data):
        reject_unknown_input(self, data)
        return super().to_internal_value(data)

    def validate(self, attrs):
        return attrs


class SourceBulkCommandSerializer(serializers.Serializer):
    entries: serializers.ListSerializer = serializers.ListSerializer(
        child=SourceSelectionSerializer(), allow_empty=False, max_length=100
    )

    def validate(self, attrs):
        reject_unknown_fields(self)
        entries = attrs["entries"]
        for field in ("source_id", "operation_id"):
            if len({entry[field] for entry in entries}) != len(entries):
                raise serializers.ValidationError(
                    {"entries": "Select each source and operation identifier once."}
                )
        return attrs


class SourceOutcomeSerializer(serializers.Serializer):
    source_id = serializers.UUIDField()
    operation_id = serializers.UUIDField()
    accepted = serializers.BooleanField()
    status_url = serializers.CharField(allow_null=True)
    error = APIErrorSerializer(allow_null=True)


class SourceBulkResultSerializer(serializers.Serializer):
    entries = SourceOutcomeSerializer(many=True)


def source_outcome(actor, values):
    outcome = {
        "source_id": values["source_id"],
        "operation_id": values["operation_id"],
        "accepted": False,
        "status_url": None,
        "error": None,
    }
    try:
        job = request_source_processing(
            actor,
            (values["operation_id"], values["source_id"]),
            values["expected_updated_at"],
        )
    except Http404:
        outcome["error"] = {
            "code": "not_found",
            "detail": "This source record is unavailable.",
            "field_errors": {},
        }
        return outcome
    except APIException as error:
        fields = error.detail if isinstance(error.detail, dict) else {}
        outcome["error"] = {
            "code": error.default_code,
            "detail": "Check the selected source fields."
            if fields
            else str(error.detail),
            "field_errors": normalized_field_errors(fields),
        }
        return outcome
    outcome.update(accepted=True, status_url=f"/api/v1/manage/jobs/{job.pk}/")
    return outcome


class ProcessSourceSelectionView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageProcessing)

    @extend_schema(
        operation_id="process_source_selection",
        request=SourceBulkCommandSerializer,
        responses={
            200: SourceBulkResultSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
        },
    )
    def post(self, request):
        parameters = SourceBulkCommandSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        outcomes = [
            source_outcome(request.user, values)
            for values in parameters.validated_data["entries"]
        ]
        return Response(SourceBulkResultSerializer({"entries": outcomes}).data)
