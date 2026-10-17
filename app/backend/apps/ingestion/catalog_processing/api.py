from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.permissions import CanManageProcessing
from apps.common.validation import reject_unknown_fields
from apps.processing.api_v1 import COMMAND_RESPONSES, accepted_operation
from apps.processing.jobs.execution_errors import ExecutionFailure

from .commands import request_catalog_processing
from .queries import catalog_processing_options


class CatalogProcessingOptionsSerializer(serializers.Serializer):
    configuration_revision = serializers.CharField(allow_null=True)
    total_sources = serializers.IntegerField()
    eligible_sources = serializers.IntegerField()
    active_operation_id = serializers.UUIDField(allow_null=True)
    latest_operation_id = serializers.UUIDField(allow_null=True)


class CatalogProcessingCommandSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    configuration_revision = serializers.RegexField(r"^[0-9a-f]{64}$")

    def validate(self, attrs):
        reject_unknown_fields(self)
        return attrs


class CatalogProcessingView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageProcessing)

    @extend_schema(
        operation_id="catalog_processing_options",
        responses={200: CatalogProcessingOptionsSerializer},
    )
    def get(self, request):
        return Response(
            CatalogProcessingOptionsSerializer(catalog_processing_options()).data
        )

    @extend_schema(
        operation_id="process_all_catalog_books",
        request=CatalogProcessingCommandSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request):
        parameters = CatalogProcessingCommandSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        try:
            job = request_catalog_processing(request.user, parameters.validated_data)
        except ExecutionFailure:
            raise ValidationError(
                {
                    "configuration_revision": "Configure the source website before processing."
                }
            ) from None
        return accepted_operation(job)
