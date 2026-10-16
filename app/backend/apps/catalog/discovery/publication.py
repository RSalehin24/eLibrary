from apps.catalog.models import Book
from apps.common.models import LifecycleState, ReviewState


def public_books():
    return Book.objects.filter(
        state=LifecycleState.PUBLISHED,
        review_state=ReviewState.APPROVED,
        deleted_at__isnull=True,
    )
