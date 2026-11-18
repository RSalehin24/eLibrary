from apps.ingestion import views as ingestion_views
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import BookSource
from apps.common.permissions import CanManageProcessing
from apps.ingestion.models import SourceCatalogEntry, SubmissionOrigin
from apps.ingestion.serializers import BulkIdsSerializer, SourceCatalogEntrySnapshotSerializer, SourceCatalogRefreshStateSerializer
from apps.ingestion.services.curation import (
    get_source_catalog_refresh_state,
    inspect_source_catalog_entry,
    source_catalog_book_source_map,
    source_catalog_entry_overview,
    source_catalog_entry_snapshots,
    source_catalog_submission_map,
    summarize_source_catalog_snapshots,
)
from apps.ingestion.services.submissions import queue_reprocess_book

from .filters import normalize_status_filter, sort_source_catalog_snapshots
from .guards import automation_manual_creation_locked_response, source_catalog_sync_locked_response


def deleted_source_catalog_entries_queryset(queryset):
    deleted_book_sources = BookSource.objects.filter(book__deleted_at__isnull=False).values("normalized_source_url")
    return queryset.filter(source_url__in=deleted_book_sources)


def truthy_query_param(raw_value, *, default):
    if raw_value is None:
        return default

    normalized = str(raw_value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def ordered_source_catalog_entries_queryset(queryset, sort_key):
    if sort_key == "created_desc":
        return queryset.order_by("-created_at", "title")
    if sort_key == "created_asc":
        return queryset.order_by("created_at", "title")
    if sort_key == "title_desc":
        return queryset.order_by("-title")
    return queryset.order_by("title")


def pagination_payload(*, total_count, page_value, limit_value):
    page_count = max(1, ((total_count - 1) // limit_value) + 1) if total_count else 1
    page_value = min(page_value, page_count)
    return page_value, {
        "page": page_value,
        "limit": limit_value,
        "total_count": total_count,
        "page_count": page_count,
        "has_previous": page_value > 1,
        "has_next": page_value < page_count,
    }


class SourceCatalogEntryListView(APIView):
    permission_classes = [CanManageProcessing]

    def get(self, request):
        queryset = SourceCatalogEntry.objects.order_by("title")
        query = request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(author_line__icontains=query))

        normalized_status_filter = normalize_status_filter(request.query_params.get("status", "").strip())
        include_summary = truthy_query_param(
            request.query_params.get("include_summary"),
            default=True,
        )
        include_sync_state = truthy_query_param(
            request.query_params.get("include_sync_state"),
            default=True,
        )
        view_mode = request.query_params.get("view", "").strip().lower()
        sort_key = request.query_params.get("sort", "").strip()
        snapshot_queryset = deleted_source_catalog_entries_queryset(queryset) if normalized_status_filter == "deleted" else queryset

        try:
            limit_value = max(1, min(int(request.query_params.get("limit", "").strip() or 180), 400))
        except (TypeError, ValueError):
            limit_value = 180
        try:
            page_value = max(1, int(request.query_params.get("page", "").strip() or 1))
        except (TypeError, ValueError):
            page_value = 1

        if view_mode == "overview" and not normalized_status_filter:
            overview_entries, summary = source_catalog_entry_overview(
                snapshot_queryset,
                entry_statuses={"failed", "requeued"},
            )
            sort_source_catalog_snapshots(overview_entries, sort_key)
            response_payload = {
                "summary": summary,
                "entries": SourceCatalogEntrySnapshotSerializer(
                    overview_entries,
                    many=True,
                ).data,
                "pagination": {
                    "page": 1,
                    "limit": len(overview_entries),
                    "total_count": len(overview_entries),
                    "page_count": 1,
                    "has_previous": False,
                    "has_next": False,
                },
            }
            if include_sync_state:
                response_payload["sync_state"] = SourceCatalogRefreshStateSerializer(
                    get_source_catalog_refresh_state()
                ).data
            return Response(response_payload)

        fast_sort_keys = {"created_desc", "created_asc", "title_asc", "title_desc"}
        if (
            not include_summary
            and normalized_status_filter in {"", "deleted"}
            and sort_key in fast_sort_keys
        ):
            ordered_queryset = ordered_source_catalog_entries_queryset(
                snapshot_queryset,
                sort_key,
            )
            total_count = ordered_queryset.count()
            page_value, pagination = pagination_payload(
                total_count=total_count,
                page_value=page_value,
                limit_value=limit_value,
            )
            start = (page_value - 1) * limit_value
            page_entries = list(ordered_queryset[start : start + limit_value])
            page_snapshots, _ = source_catalog_entry_snapshots(page_entries)
            response_payload = {
                "entries": SourceCatalogEntrySnapshotSerializer(
                    page_snapshots,
                    many=True,
                ).data,
                "pagination": pagination,
            }
            if include_sync_state:
                response_payload["sync_state"] = SourceCatalogRefreshStateSerializer(
                    get_source_catalog_refresh_state()
                ).data
            return Response(response_payload)

        snapshots, _ = source_catalog_entry_snapshots(snapshot_queryset)
        if normalized_status_filter and normalized_status_filter != "deleted":
            snapshots = [
                snapshot
                for snapshot in snapshots
                if normalize_status_filter(snapshot["curation_status"])
                == normalized_status_filter
            ]
        summary = summarize_source_catalog_snapshots(snapshots)
        sort_source_catalog_snapshots(snapshots, sort_key)

        total_count = len(snapshots)
        page_value, pagination = pagination_payload(
            total_count=total_count,
            page_value=page_value,
            limit_value=limit_value,
        )
        start = (page_value - 1) * limit_value
        page_entries = snapshots[start : start + limit_value]

        response_payload = {
            "entries": SourceCatalogEntrySnapshotSerializer(page_entries, many=True).data,
            "pagination": pagination,
        }
        if include_summary:
            response_payload["summary"] = summary
        if include_sync_state:
            response_payload["sync_state"] = SourceCatalogRefreshStateSerializer(
                get_source_catalog_refresh_state()
            ).data
        return Response(response_payload)


class SourceCatalogEntryDetailView(APIView):
    permission_classes = [CanManageProcessing]

    def delete(self, request, pk):
        entry = get_object_or_404(SourceCatalogEntry, pk=pk)
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SourceCatalogEntryBulkDeleteView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queryset = SourceCatalogEntry.objects.filter(pk__in=serializer.validated_data["ids"])
        deleted_count = queryset.count()
        queryset.delete()
        return Response(
            {
                "deleted_count": deleted_count,
                "skipped_missing": max(len(serializer.validated_data["ids"]) - deleted_count, 0),
            }
        )


class SourceCatalogEntryCreateBooksView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        locked_response = automation_manual_creation_locked_response() or source_catalog_sync_locked_response()
        if locked_response:
            return locked_response

        entries = list(SourceCatalogEntry.objects.filter(pk__in=serializer.validated_data["ids"]).order_by("title"))
        source_urls = [entry.source_url for entry in entries]
        source_map = source_catalog_book_source_map(source_urls)
        submission_map = source_catalog_submission_map(source_urls)
        summary = {
            "queued_creates": 0,
            "queued_updates": 0,
            "skipped_ready": 0,
            "skipped_processing": 0,
            "skipped_deleted": 0,
            "skipped_missing": max(len(serializer.validated_data["ids"]) - len(entries), 0),
            "errors": [],
        }

        for entry in entries:
            inspection = inspect_source_catalog_entry(entry, source_map, submission_map)
            status_value = inspection["curation_status"]
            try:
                if status_value == "processing":
                    summary["skipped_processing"] += 1
                    continue
                if inspection["local_book"] is None or status_value == "deleted":
                    ingestion_views.create_submission_records(
                        submitter=request.user,
                        parsed_entries=[{"kind": "url", "value": entry.source_url}],
                        auto_process=True,
                        origin=SubmissionOrigin.CURATION,
                    )
                    summary["queued_creates"] += 1
                    continue
                if status_value in {"unfinished", "failed", "stopped"}:
                    _, created = queue_reprocess_book(inspection["local_book"], actor=request.user, origin=SubmissionOrigin.CURATION)
                    if created:
                        summary["queued_updates"] += 1
                    else:
                        summary["skipped_processing"] += 1
                    continue
                summary["skipped_ready"] += 1
            except Exception as exc:
                if len(summary["errors"]) < 20:
                    summary["errors"].append({"source_url": entry.source_url, "error": str(exc)})

        return Response(summary, status=status.HTTP_202_ACCEPTED)


__all__ = [
    "SourceCatalogEntryBulkDeleteView",
    "SourceCatalogEntryCreateBooksView",
    "SourceCatalogEntryDetailView",
    "SourceCatalogEntryListView",
]
