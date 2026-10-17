from django.db.models import Case, FloatField, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce, NullIf

from apps.access.book_permissions import books_with_scopes
from apps.access.models import PermissionScope, ReadingSession
from apps.catalog.discovery.publication import public_books
from apps.catalog.models import Book, PhysicalReadingLog, SavedBook

READER_SCOPES = [
    PermissionScope.READ_DURABLE,
    PermissionScope.READ_ONCE,
    PermissionScope.PREVIEW_HTML,
    PermissionScope.DOWNLOAD_FILE,
    PermissionScope.SEND_KINDLE,
]


def granted_books(actor):
    digital = books_with_scopes(actor, READER_SCOPES)
    paper = books_with_scopes(actor, [PermissionScope.PHYSICAL_BOOKS_VIEW]).filter(
        record_type="manual"
    )
    return Book.objects.filter(
        Q(pk__in=digital.values("pk")) | Q(pk__in=paper.values("pk"))
    )


def visible_personal_books(actor):
    if not actor.is_active:
        return Book.objects.none()
    return (
        Book.objects.filter(deleted_at__isnull=True)
        .filter(
            Q(pk__in=public_books().values("pk"))
            | Q(user_books__user=actor)
            | Q(pk__in=granted_books(actor).values("pk"))
        )
        .distinct()
    )


def physical_progress(actor):
    return PhysicalReadingLog.objects.filter(
        user=actor, book_id=OuterRef("pk")
    ).annotate(
        percent=Case(
            When(status="finished", then=Value(100.0)),
            default=100.0 * Coalesce("current_page", 0) / NullIf("total_pages", 0),
            output_field=FloatField(),
        )
    )


def annotate_personal_books(queryset, actor):
    digital = ReadingSession.objects.filter(user=actor, book_id=OuterRef("pk"))
    paper = physical_progress(actor)
    return queryset.annotate(
        progress_percent=Coalesce(
            Subquery(digital.values("progress_percent")[:1]),
            Subquery(paper.values("percent")[:1]),
        ),
        last_location=Subquery(digital.values("last_location")[:1]),
        activity_at=Coalesce(
            Subquery(digital.values("last_opened_at")[:1]),
            Subquery(paper.values("updated_at")[:1]),
        ),
    )


def personal_feed(actor, view):
    if view == "owned":
        return (
            Book.objects.filter(user_books__user=actor, deleted_at__isnull=True)
            if actor.is_active
            else Book.objects.none()
        )
    visible = visible_personal_books(actor)
    if view == "all":
        return visible.filter(
            Q(user_books__user=actor)
            | Q(saved_by__user=actor)
            | Q(reading_sessions__user=actor)
            | Q(physical_reading_logs__user=actor)
        ).distinct()
    if view == "saved":
        return visible.filter(
            pk__in=SavedBook.objects.filter(user=actor).values("book_id")
        )
    if view == "granted":
        return visible.filter(pk__in=granted_books(actor).values("pk"))
    return visible.filter(
        Q(reading_sessions__user=actor) | Q(physical_reading_logs__user=actor)
    ).distinct()
