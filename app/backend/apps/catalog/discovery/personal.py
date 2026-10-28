from django.db.models import OuterRef, Q, Subquery

from apps.access.book_permissions import books_with_scopes
from apps.access.models import PermissionScope, ReadingSession
from apps.catalog.discovery.publication import public_books
from apps.catalog.models import Book, SavedBook

READER_SCOPES = [
    PermissionScope.READ_DURABLE,
    PermissionScope.READ_ONCE,
    PermissionScope.PREVIEW_HTML,
    PermissionScope.DOWNLOAD_FILE,
    PermissionScope.SEND_KINDLE,
]


def granted_books(actor):
    return books_with_scopes(actor, READER_SCOPES)


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


def annotate_personal_books(queryset, actor):
    sessions = ReadingSession.objects.filter(user=actor, book_id=OuterRef("pk"))
    return queryset.annotate(
        progress_percent=Subquery(sessions.values("progress_percent")[:1]),
        last_location=Subquery(sessions.values("last_location")[:1]),
        activity_at=Subquery(sessions.values("last_opened_at")[:1]),
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
        ).distinct()
    if view == "saved":
        return visible.filter(
            pk__in=SavedBook.objects.filter(user=actor).values("book_id")
        )
    if view == "granted":
        return visible.filter(pk__in=granted_books(actor).values("pk"))
    return visible.filter(reading_sessions__user=actor).distinct()
