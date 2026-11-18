from apps.ingestion import views as ingestion_views
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import CanManageProcessing
from apps.ingestion.models import CatalogCurationRun, JobStatus
from apps.ingestion.serializers import (
    BulkIdsSerializer,
    CatalogAutomationSettingsSerializer,
    CatalogAutomationSettingsUpdateSerializer,
    CatalogCurationRunCreateSerializer,
    CatalogCurationRunSerializer,
    SourceCatalogRefreshStateSerializer,
)
from apps.ingestion.services.curation import (
    begin_source_catalog_refresh,
    cancel_catalog_curation_run,
    cancel_source_catalog_refresh,
    get_catalog_automation_settings,
    get_source_catalog_refresh_state,
)

from .filters import normalize_status_filter
from .guards import automation_manual_creation_locked_response
from .querysets import runs_ordered_queryset


class CatalogCurationRunListCreateView(APIView):
    permission_classes = [CanManageProcessing]

    def get(self, request):
        queryset = CatalogCurationRun.objects.select_related("requested_by")
        trigger = request.query_params.get("trigger", "").strip()
        if trigger:
            queryset = queryset.filter(trigger=trigger)
        status_filter = normalize_status_filter(request.query_params.get("status", "").strip())
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        mode = request.query_params.get("mode", "").strip()
        if mode:
            queryset = queryset.filter(mode=mode)
        query = request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(requested_by__email__icontains=query) | Q(last_error__icontains=query))
        limit = request.query_params.get("limit", "").strip()
        try:
            limit_value = max(1, min(int(limit), 50)) if limit else 12
        except (TypeError, ValueError):
            limit_value = 12
        runs = runs_ordered_queryset(queryset)[:limit_value]
        return Response(CatalogCurationRunSerializer(runs, many=True).data)

    def post(self, request):
        locked_response = automation_manual_creation_locked_response()
        if locked_response:
            return locked_response
        serializer = CatalogCurationRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = ingestion_views.create_catalog_curation_run(
            mode=serializer.validated_data["mode"],
            requested_by=request.user,
            refresh_catalog=serializer.validated_data["refresh_catalog"],
            refresh_max_pages=serializer.validated_data["refresh_max_pages"],
        )
        return Response(CatalogCurationRunSerializer(run).data, status=status.HTTP_202_ACCEPTED)


class CatalogCurationRunStopView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request, pk):
        return Response(CatalogCurationRunSerializer(cancel_catalog_curation_run(get_object_or_404(CatalogCurationRun, pk=pk))).data)


class CatalogCurationRunDetailView(APIView):
    permission_classes = [CanManageProcessing]

    def delete(self, request, pk):
        run = get_object_or_404(CatalogCurationRun, pk=pk)
        if run.status in {JobStatus.QUEUED, JobStatus.PROCESSING}:
            return Response({"detail": "Stop this run before deleting it."}, status=status.HTTP_400_BAD_REQUEST)
        run.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CatalogCurationRunBulkStopView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        runs = list(CatalogCurationRun.objects.filter(pk__in=serializer.validated_data["ids"]))
        stopped_count = 0
        skipped_complete = 0
        for run in runs:
            previous_status = run.status
            run = cancel_catalog_curation_run(run)
            if previous_status == run.status and run.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
                skipped_complete += 1
                continue
            stopped_count += 1
        return Response(
            {
                "stopped_count": stopped_count,
                "skipped_complete": skipped_complete,
                "skipped_missing": max(len(serializer.validated_data["ids"]) - len(runs), 0),
            }
        )


class CatalogCurationRunBulkDeleteView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        runs = list(CatalogCurationRun.objects.filter(pk__in=serializer.validated_data["ids"]))
        deleted_count = 0
        skipped_active = 0
        for run in runs:
            if run.status in {JobStatus.QUEUED, JobStatus.PROCESSING}:
                skipped_active += 1
                continue
            run.delete()
            deleted_count += 1
        return Response(
            {
                "deleted_count": deleted_count,
                "skipped_active": skipped_active,
                "skipped_missing": max(len(serializer.validated_data["ids"]) - len(runs), 0),
            }
        )


class CatalogAutomationSettingsView(APIView):
    permission_classes = [CanManageProcessing]

    def get(self, request):
        settings_obj = get_catalog_automation_settings()
        latest_run = CatalogCurationRun.objects.filter(trigger="scheduled").select_related("requested_by").first()
        return Response(
            {
                "settings": CatalogAutomationSettingsSerializer(settings_obj).data,
                "latest_run": CatalogCurationRunSerializer(latest_run).data if latest_run else None,
            }
        )

    def patch(self, request):
        settings_obj = get_catalog_automation_settings()
        serializer = CatalogAutomationSettingsUpdateSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        settings_obj = serializer.save(updated_by=request.user)
        latest_run = CatalogCurationRun.objects.filter(trigger="scheduled").select_related("requested_by").first()
        return Response(
            {
                "settings": CatalogAutomationSettingsSerializer(settings_obj).data,
                "latest_run": CatalogCurationRunSerializer(latest_run).data if latest_run else None,
            }
        )


class SourceCatalogRefreshView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        locked_response = automation_manual_creation_locked_response()
        if locked_response:
            return locked_response
        try:
            max_pages = int(request.data.get("max_pages") or request.query_params.get("max_pages") or 3)
        except (TypeError, ValueError):
            return Response({"detail": "max_pages must be a whole number."}, status=status.HTTP_400_BAD_REQUEST)
        sync_state, _ = begin_source_catalog_refresh(requested_by=request.user, max_pages=max_pages)
        return Response(SourceCatalogRefreshStateSerializer(sync_state).data, status=status.HTTP_202_ACCEPTED)


class SourceCatalogRefreshStopView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        return Response(SourceCatalogRefreshStateSerializer(cancel_source_catalog_refresh()).data)


__all__ = [
    "CatalogAutomationSettingsView",
    "CatalogCurationRunBulkDeleteView",
    "CatalogCurationRunBulkStopView",
    "CatalogCurationRunDetailView",
    "CatalogCurationRunListCreateView",
    "CatalogCurationRunStopView",
    "SourceCatalogRefreshStopView",
    "SourceCatalogRefreshView",
]
