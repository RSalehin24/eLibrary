from django.db.models import Exists, OuterRef, Prefetch

from apps.access.book_permissions import books_with_scopes
from apps.access.models import PermissionScope
from apps.access.storage import asset_is_available
from apps.catalog.content_quality import book_is_quarantined
from apps.catalog.discovery.personal import visible_personal_books
from apps.catalog.models import GeneratedAsset, SavedBook, UserBook


def list_control_books(actor, slugs):
    kindle = books_with_scopes(
        actor, [PermissionScope.SEND_KINDLE, PermissionScope.ADMIN_FULL_CONTROL]
    )
    assets = GeneratedAsset.objects.filter(asset_type="epub", status="ready").only(
        "id", "book_id", "file", "legacy_path"
    )
    return (
        visible_personal_books(actor)
        .filter(slug__in=slugs)
        .only("id", "slug", "record_type", "source_quality_state")
        .annotate(
            saved=Exists(SavedBook.objects.filter(user=actor, book_id=OuterRef("pk"))),
            owned=Exists(UserBook.objects.filter(user=actor, book_id=OuterRef("pk"))),
            kindle_granted=Exists(kindle.filter(pk=OuterRef("pk"))),
        )
        .prefetch_related(
            Prefetch("generated_assets", queryset=assets, to_attr="list_assets")
        )
    )


def book_list_controls(actor, slugs):
    return [
        {
            "slug": book.slug,
            "saved": book.saved,
            "can_send_kindle": bool(
                book.record_type == "digital"
                and not book_is_quarantined(book)
                and (book.owned or book.kindle_granted)
                and any(asset_is_available(asset) for asset in book.list_assets)
            ),
        }
        for book in list_control_books(actor, slugs)
    ]
