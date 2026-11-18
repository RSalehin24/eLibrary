from django.db.models import OuterRef, Prefetch, Q, Subquery
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Book, BookCategory, BookContributor, BookSource, ContributorRole
from apps.common.permissions import CanManageProcessing
from apps.ingestion.models import ProcessingJob, SourceCatalogEntry, SubmissionOrigin
from apps.ingestion.serializers import BulkIdsSerializer
from apps.ingestion.services.submissions import queue_reprocess_book

from .filters import INCOMPLETE_CATEGORY_KEYWORDS, has_incomplete_keyword
from .guards import automation_manual_creation_locked_response


class IncompleteCatalogCheckListView(APIView):
    permission_classes = [CanManageProcessing]

    def get(self, request):
        incomplete_category_filter = Q()
        for keyword in INCOMPLETE_CATEGORY_KEYWORDS:
            incomplete_category_filter |= Q(book_categories__category__name__icontains=keyword)

        latest_job_queryset = ProcessingJob.objects.filter(book=OuterRef("pk")).order_by("-created_at")
        books = list(
            Book.objects.filter(deleted_at__isnull=True)
            .filter(incomplete_category_filter)
            .distinct()
            .only("id", "title", "slug", "updated_at")
            .annotate(
                latest_job_status=Subquery(latest_job_queryset.values("status")[:1]),
                latest_job_error=Subquery(latest_job_queryset.values("last_error")[:1]),
                latest_job_type=Subquery(latest_job_queryset.values("job_type")[:1]),
            )
            .prefetch_related(
                Prefetch("book_categories", queryset=BookCategory.objects.select_related("category").only("book_id", "category_id", "category__name")),
                Prefetch(
                    "source_urls",
                    queryset=BookSource.objects.only("book_id", "normalized_source_url", "created_at").order_by("-created_at"),
                    to_attr="prefetched_source_urls",
                ),
                Prefetch(
                    "book_contributors",
                    queryset=BookContributor.objects.filter(role=ContributorRole.AUTHOR)
                    .select_related("contributor")
                    .only("book_id", "role", "sort_order", "contributor_id", "contributor__name")
                    .order_by("sort_order", "contributor__name"),
                    to_attr="prefetched_author_relations",
                ),
            )
            .order_by("title")
        )

        source_urls = []
        for book in books:
            source = next(iter(getattr(book, "prefetched_source_urls", [])), None)
            if source and source.normalized_source_url:
                source_urls.append(source.normalized_source_url)

        entry_map = {entry.source_url: entry for entry in SourceCatalogEntry.objects.filter(source_url__in=source_urls).only("id", "source_url", "raw_data")}
        rows = []
        summary = {
            "total_incomplete_books": 0,
            "removed_from_unfinished": 0,
            "still_in_unfinished": 0,
            "missing_in_catalog": 0,
            "queued": 0,
            "processing": 0,
            "failed": 0,
            "stopped": 0,
        }

        for book in books:
            local_categories = ", ".join(relation.category.name for relation in book.book_categories.all() if relation.category_id and relation.category and relation.category.name)
            if not has_incomplete_keyword(local_categories):
                continue
            source = next(iter(getattr(book, "prefetched_source_urls", [])), None)
            source_url = source.normalized_source_url if source else ""
            entry = entry_map.get(source_url)
            source_categories = ""
            if entry:
                raw_data = entry.raw_data or {}
                source_categories = (raw_data.get("category") or raw_data.get("book_type") or "").strip()

            removed_from_unfinished = bool(entry) and not has_incomplete_keyword(source_categories)
            latest_status = book.latest_job_status or ""
            summary["total_incomplete_books"] += 1
            if removed_from_unfinished:
                summary["removed_from_unfinished"] += 1
            elif entry:
                summary["still_in_unfinished"] += 1
            else:
                summary["missing_in_catalog"] += 1

            if latest_status in {"queued", "processing", "failed", "cancelled"}:
                summary["stopped" if latest_status == "cancelled" else latest_status] += 1

            author_names = [
                relation.contributor.name
                for relation in getattr(book, "prefetched_author_relations", [])
                if relation.role == ContributorRole.AUTHOR and relation.contributor_id and relation.contributor and relation.contributor.name
            ]
            rows.append(
                {
                    "book_id": str(book.id),
                    "book_title": book.title,
                    "book_slug": book.slug,
                    "author_line": ", ".join(author_names),
                    "local_categories": local_categories,
                    "source_url": source_url,
                    "source_categories": source_categories,
                    "catalog_entry_id": str(entry.id) if entry else "",
                    "removed_from_unfinished": removed_from_unfinished,
                    "latest_job_status": "stopped" if latest_status == "cancelled" else latest_status,
                    "latest_job_error": book.latest_job_error or "",
                    "updated_at": book.updated_at,
                }
            )

        query = request.query_params.get("q", "").strip().lower()
        if query:
            rows = [row for row in rows if query in row["book_title"].lower() or query in (row["author_line"] or "").lower() or query in (row["source_categories"] or "").lower()]

        status_filter = request.query_params.get("status", "").strip().lower()
        if status_filter == "removed":
            rows = [row for row in rows if row["removed_from_unfinished"]]
        elif status_filter == "still":
            rows = [row for row in rows if row["catalog_entry_id"] and not row["removed_from_unfinished"]]
        elif status_filter == "missing":
            rows = [row for row in rows if not row["catalog_entry_id"]]

        rows.sort(key=lambda row: (0 if row["removed_from_unfinished"] else 1, row.get("book_title") or ""))
        return Response({"summary": summary, "entries": rows})


class IncompleteCatalogCheckCreateBooksView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        locked_response = automation_manual_creation_locked_response()
        if locked_response:
            return locked_response

        books = list(Book.objects.filter(pk__in=serializer.validated_data["ids"], deleted_at__isnull=True))
        summary = {
            "queued_updates": 0,
            "skipped_processing": 0,
            "skipped_missing": max(len(serializer.validated_data["ids"]) - len(books), 0),
            "errors": [],
        }

        for book in books:
            try:
                _, created = queue_reprocess_book(book, actor=request.user, origin=SubmissionOrigin.CURATION)
                if created:
                    summary["queued_updates"] += 1
                else:
                    summary["skipped_processing"] += 1
            except Exception as exc:
                if len(summary["errors"]) < 20:
                    summary["errors"].append({"book_id": str(book.id), "error": str(exc)})

        return Response(summary, status=status.HTTP_202_ACCEPTED)


__all__ = ["IncompleteCatalogCheckCreateBooksView", "IncompleteCatalogCheckListView"]
