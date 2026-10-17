from apps.catalog.models import Book
from apps.common.models import LifecycleState, ReviewState


def public_books():
    return Book.objects.filter(
        state=LifecycleState.PUBLISHED,
        deleted_at__isnull=True,
    ).exclude(review_state=ReviewState.REJECTED)
