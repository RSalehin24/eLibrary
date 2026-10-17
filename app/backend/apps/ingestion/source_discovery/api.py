from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.permissions import CanManageProcessing
from apps.common.validation import reject_unknown_fields
from apps.processing.api_v1 import COMMAND_RESPONSES, accepted_operation
from apps.processing.jobs.execution_errors import ExecutionFailure

from .commands import request_source_discovery
from .configuration import DEFAULT_DISCOVERY_PAGES, MAX_DISCOVERY_PAGES
from .queries import discovery_options


class SourceDiscoveryOptionsSerializer(serializers.Serializer):
    configured = serializers.BooleanField(default=True)
    catalog_url = serializers.URLField(allow_null=True)
    configuration_revision = serializers.CharField(allow_null=True)
    default_max_pages = serializers.IntegerField()
    maximum_pages = serializers.IntegerField()
    active_operation_id = serializers.UUIDField(allow_null=True)
    latest_operation_id = serializers.UUIDField(allow_null=True)


class SourceDiscoveryScopeSerializer(serializers.Serializer):
    catalog_scope = serializers.ChoiceField(
        choices=("all", "unfinished"), default="all"
    )


class SourceDiscoveryCommandSerializer(SourceDiscoveryScopeSerializer):
    operation_id = serializers.UUIDField()
    configuration_revision = serializers.RegexField(r"^[0-9a-f]{64}$")
    max_pages = serializers.IntegerField(
        min_value=1, max_value=MAX_DISCOVERY_PAGES, default=DEFAULT_DISCOVERY_PAGES
    )
    fetch_all = serializers.BooleanField(default=False)

    def validate(self, attrs):
        reject_unknown_fields(self)
        return attrs


class SourceDiscoveryView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageProcessing)

    @extend_schema(
        operation_id="source_discovery_options",
        parameters=[SourceDiscoveryScopeSerializer],
        responses={200: SourceDiscoveryOptionsSerializer, 403: APIErrorSerializer},
    )
    def get(self, request):
        parameters = SourceDiscoveryScopeSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        try:
            values = discovery_options(parameters.validated_data["catalog_scope"])
        except ExecutionFailure:
            values = {
                "configured": False,
                "catalog_url": None,
                "configuration_revision": None,
                "default_max_pages": DEFAULT_DISCOVERY_PAGES,
                "maximum_pages": MAX_DISCOVERY_PAGES,
                "active_operation_id": None,
                "latest_operation_id": None,
            }
        return Response(SourceDiscoveryOptionsSerializer(values).data)

    @extend_schema(
        operation_id="source_discovery_request",
        request=SourceDiscoveryCommandSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request):
        parameters = SourceDiscoveryCommandSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        try:
            job = request_source_discovery(request.user, parameters.validated_data)
        except ExecutionFailure:
            raise ValidationError(
                {
                    "configuration_revision": "Configure an allowed HTTPS source catalog before discovery."
                }
            ) from None
        return accepted_operation(job)
