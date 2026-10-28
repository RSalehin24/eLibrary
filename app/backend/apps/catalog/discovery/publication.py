from apps.catalog.models import Book
from apps.common.models import LifecycleState


def public_books():
    return (
        Book.objects.filter(
            state=LifecycleState.PUBLISHED,
            deleted_at__isnull=True,
        )
        .exclude()
        .exclude(source_quality_state="quarantined")
    )
