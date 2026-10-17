from django.db.models import Count, IntegerField, Q
from django.db.models.functions import Cast, Coalesce
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import AdminPaginationSerializer, APIErrorSerializer
from apps.common.pagination import BoundedAdminPagination
from apps.common.permissions import CanManageProcessing
from apps.processing.automation_models import AutomationRun, SourceAutomation

from .serializers import (
    AutomationCreateSerializer,
    AutomationRunSerializer,
    AutomationSerializer,
    AutomationUpdateSerializer,
)
from .services import create_automation, update_automation


class AutomationParametersSerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)


class AutomationCollectionSerializer(serializers.Serializer):
    entries = AutomationSerializer(many=True)
    pagination = AdminPaginationSerializer()


class AutomationRunCollectionSerializer(serializers.Serializer):
    entries = AutomationRunSerializer(many=True)
    pagination = AdminPaginationSerializer()


def automation_queryset():
    return SourceAutomation.objects.select_related("run_as").only(
        "id",
        "name",
        "enabled",
        "frequency",
        "first_run_at",
        "time_zone",
        "next_run_at",
        "source_max_pages",
        "processing_limit",
        "fetch_all",
        "process_all",
        "run_as_id",
        "updated_at",
        "run_as__id",
        "run_as__full_name",
        "run_as__email",
    )


def automation_runs(automation):
    return (
        automation.runs.select_related("job")
        .only(
            "id",
            "automation_id",
            "due_at",
            "state",
            "error_code",
            "job_id",
            "job__id",
            "job__state",
            "processing_limit",
            "process_all",
            "job__checkpoint",
            "missed_occurrences",
            "created_at",
        )
        .annotate(
            processing_count=Count(
                "processing_jobs", filter=Q(processing_jobs__kind="process_source")
            ),
            processing_active=Count(
                "processing_jobs",
                filter=Q(
                    processing_jobs__kind="process_source",
                    processing_jobs__state__in=["queued", "running", "retry_wait"],
                ),
            ),
            processing_attention=Count(
                "processing_jobs",
                filter=Q(
                    processing_jobs__kind="process_source",
                    processing_jobs__state__in=["failed", "needs_attention", "paused"],
                ),
            ),
            processing_succeeded=Count(
                "processing_jobs",
                filter=Q(
                    processing_jobs__kind="process_source",
                    processing_jobs__state="succeeded",
                ),
            ),
            processing_rejected=Coalesce(
                Cast("job__checkpoint__automation_rejected_count", IntegerField()), 0
            ),
        )
        .order_by("-due_at", "-id")
    )


class AutomationListView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageProcessing)

    @extend_schema(
        operation_id="automations_list",
        parameters=[AutomationParametersSerializer],
        responses={200: AutomationCollectionSerializer},
    )
    def get(self, request):
        parameters = AutomationParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        page = BoundedAdminPagination()
        return page.get_paginated_response(
            AutomationSerializer(
                page.paginate_queryset(automation_queryset(), request), many=True
            ).data
        )

    @extend_schema(
        operation_id="automation_create",
        request=AutomationCreateSerializer,
        responses={
            201: AutomationSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def post(self, request):
        return Response(
            AutomationSerializer(create_automation(request.user, request.data)).data,
            status=201,
        )


class AutomationDetailView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageProcessing)

    @extend_schema(
        operation_id="automation_detail",
        responses={200: AutomationSerializer, 404: APIErrorSerializer},
    )
    def get(self, request, identifier):
        return Response(
            AutomationSerializer(
                get_object_or_404(automation_queryset(), pk=identifier)
            ).data
        )

    @extend_schema(
        operation_id="automation_update",
        request=AutomationUpdateSerializer,
        responses={
            200: AutomationSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def patch(self, request, identifier):
        return Response(
            AutomationSerializer(
                update_automation(request.user, identifier, request.data)
            ).data
        )


class AutomationRunsView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageProcessing)

    @extend_schema(
        operation_id="automation_runs",
        parameters=[AutomationParametersSerializer],
        responses={200: AutomationRunCollectionSerializer, 404: APIErrorSerializer},
    )
    def get(self, request, identifier):
        automation = get_object_or_404(SourceAutomation, pk=identifier)
        parameters = AutomationParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        page = BoundedAdminPagination()
        entries: list[AutomationRun] | None = page.paginate_queryset(
            automation_runs(automation), request
        )
        return page.get_paginated_response(
            AutomationRunSerializer(entries, many=True).data
        )
