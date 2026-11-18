from django.utils import timezone

from apps.access.models import PermissionScope, PreviewAccessSession
from apps.common.permissions import user_has_scope


def can_manage_processing_records(user):
    return bool(
        user.is_staff or user_has_scope(user, [PermissionScope.PROCESSING_MANAGE])
    )


def ensure_preview_session(user, book, submission=None, allow_guest=False):
    if not user and not allow_guest:
        return None

    filters = {
        "book": book,
        "expires_at__gt": timezone.now(),
    }
    if user:
        filters["user"] = user
    else:
        filters["user__isnull"] = True
        if submission is not None:
            filters["source_submission"] = submission

    existing_session = (
        PreviewAccessSession.objects.filter(**filters)
        .order_by("-created_at")
        .first()
    )
    if existing_session:
        return existing_session
    return PreviewAccessSession.objects.create(
        user=user if user else None,
        book=book,
        source_submission=submission,
    )
