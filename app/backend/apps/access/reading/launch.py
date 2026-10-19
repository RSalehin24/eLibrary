from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.access.models import (
    BookOpeningRecord,
    PermissionScope,
    PreviewAccessSession,
    default_preview_expiry,
)
from apps.accounts.models import User
from apps.common.permissions import (
    user_can_launch_reader,
    user_can_view_preview_html,
    user_has_read_once_limit,
    user_has_scope,
    user_owns_book,
)


def lock_reader_account(user):
    # Both launch and HTML preview must serialize consumption of read-once access.
    return (
        User.objects.only("id", "is_staff", "is_superuser")
        .select_for_update()
        .get(pk=user.pk)
    )


def consume_read_once(user, book):
    if user.is_staff or user.is_superuser or user_owns_book(user, book):
        return
    if user_has_scope(user, [PermissionScope.READ_DURABLE], book=book):
        return
    if user_has_scope(user, [PermissionScope.READ_ONCE], book=book):
        BookOpeningRecord.objects.get_or_create(user=user, book=book)


def ensure_read_once_available(user, book):
    if user_has_read_once_limit(user, book):
        raise PermissionDenied(
            "You have already opened this book under the Read Once permission."
        )


@transaction.atomic
def launch_reader_session(user, book):
    from apps.catalog.content_quality import book_is_quarantined
    if book_is_quarantined(book):
        raise PermissionDenied("This book is temporarily unavailable while its content is repaired.")
    user = lock_reader_account(user)
    ensure_read_once_available(user, book)
    session = active_reader_session(user, book)
    if not user_can_launch_reader(user, book) and session is None:
        raise PermissionDenied("You do not have reader access for this book.")
    consume_read_once(user, book)
    if session is None:
        session = PreviewAccessSession.objects.create(user=user, book=book)
    session.launch_count += 1
    session.expires_at = default_preview_expiry()
    session.save(update_fields=["launch_count", "expires_at", "updated_at"])
    return session


def active_reader_session(user, book):
    return (
        PreviewAccessSession.objects.filter(
            user=user, book=book, expires_at__gt=timezone.now()
        )
        .order_by("-created_at")
        .first()
    )


@transaction.atomic
def authorize_html_opening(user, book):
    user = lock_reader_account(user)
    ensure_read_once_available(user, book)
    if not user_can_view_preview_html(user, book):
        raise PermissionDenied("You do not have download access for this book.")
    consume_read_once(user, book)
