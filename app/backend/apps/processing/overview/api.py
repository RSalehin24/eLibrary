from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer

from .queries import management_overview, overview_work
from .serializers import ManagementOverviewSerializer, OverviewWorkSerializer


class ManagementOverviewView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="management_overview",
        responses={200: ManagementOverviewSerializer, 403: APIErrorSerializer},
    )
    def get(self, request):
        return Response(
            ManagementOverviewSerializer(management_overview(request.user)).data
        )


class OverviewWorkView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="management_overview_work",
        responses={200: OverviewWorkSerializer, 403: APIErrorSerializer},
    )
    def get(self, request):
        return Response(OverviewWorkSerializer(overview_work(request.user)).data)
