from dataclasses import dataclass

from django.db.models import BooleanField, Case, Exists, OuterRef, Q, Subquery, When

from apps.catalog.discovery.management import metadata_managed_books
from apps.catalog.models import Book, BookSource
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.job_models import SOURCE_ACTIVE_STATES, BackgroundJob


@dataclass(frozen=True)
class SourceSnapshot:
    entry: SourceCatalogEntry
    book: Book | None
    can_edit_book: bool


def source_entries(parameters):
    matches = BookSource.objects.filter(normalized_source_url=OuterRef("source_url"))
    operations = BackgroundJob.objects.filter(source_record_id=OuterRef("pk"))
    queryset = (
        SourceCatalogEntry.objects.annotate(
            active_operation_id=Subquery(
                operations.filter(state__in=SOURCE_ACTIVE_STATES).values("pk")[:1]
            ),
            latest_operation_id=Subquery(operations.values("pk")[:1]),
            linked=Q(catalog_book__isnull=False) | Exists(matches),
            removed=Case(
                When(
                    catalog_book__isnull=False,
                    then=Q(catalog_book__deleted_at__isnull=False),
                ),
                default=Exists(matches.filter(book__deleted_at__isnull=False)),
                output_field=BooleanField(),
            ),
        )
        .defer("raw_data")
        .order_by("normalized_title", "id")
    )
    query = parameters["q"]
    queryset = queryset.filter(
        Q(title__icontains=query) | Q(author_line__icontains=query)
    )
    filters = {
        "unlinked": {"linked": False},
        "linked": {"linked": True, "removed": False},
        "removed": {"removed": True},
    }
    queryset = queryset.filter(**filters.get(parameters["status"], {}))
    if parameters.get("catalog_scope") == "unfinished":
        from .unfinished import unfinished_source_query

        queryset = queryset.filter(unfinished_source_query())
    return queryset


def source_book_map(entries):
    return {
        source.normalized_source_url: source.book
        for source in BookSource.objects.select_related("book")
        .filter(normalized_source_url__in=[entry.source_url for entry in entries])
        .only(
            "normalized_source_url",
            "book_id",
            "book__id",
            "book__title",
            "book__slug",
            "book__state",
            "book__deleted_at",
        )
    }


def editable_source_books(actor, books):
    return set(
        metadata_managed_books(actor)
        .filter(pk__in=[book.pk for book in books.values()])
        .values_list("pk", flat=True)
    )


def source_snapshots(entries, actor):
    books = source_book_map(entries)
    direct = {
        book.pk: book
        for book in Book.objects.filter(
            pk__in=[entry.catalog_book_id for entry in entries]
        ).only("id", "title", "slug", "state", "deleted_at")
    }
    books.update(
        {
            entry.source_url: direct[entry.catalog_book_id]
            for entry in entries
            if entry.catalog_book_id in direct
        }
    )
    editable = editable_source_books(actor, books)
    return [
        SourceSnapshot(
            entry,
            books.get(entry.source_url),
            books.get(entry.source_url) is not None
            and books[entry.source_url].pk in editable,
        )
        for entry in entries
    ]
