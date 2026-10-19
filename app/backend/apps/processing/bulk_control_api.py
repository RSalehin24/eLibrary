from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.permissions import CanManageProcessing
from apps.processing.bulk_control_serializers import (
    BulkJobControlResultSerializer,
    BulkJobControlSerializer,
)
from apps.processing.jobs.bulk_controls import control_job_selection


class BulkJobControlView(VersionedAPIView):
    permission_classes = (CanManageProcessing,)

    @extend_schema(
        operation_id="managed_jobs_bulk_control",
        request=BulkJobControlSerializer,
        responses={
            200: BulkJobControlResultSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def post(self, request):
        parameters = BulkJobControlSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        return Response(control_job_selection(request.user, parameters.validated_data))
