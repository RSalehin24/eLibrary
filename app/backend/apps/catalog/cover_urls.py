from django.db.models import OuterRef, Subquery
from django.urls import reverse

from apps.catalog.models import GeneratedAsset


def with_cover_asset(queryset):
    covers = GeneratedAsset.objects.filter(
        book_id=OuterRef("pk"), asset_type="cover", status="ready"
    )
    return queryset.annotate(
        cover_asset_id=Subquery(covers.values("pk")[:1]),
        cover_updated_at=Subquery(covers.values("updated_at")[:1]),
    )


def book_cover_url(book):
    if not getattr(book, "cover_asset_id", None):
        return None
    url = reverse("api_v1:book-cover", kwargs={"slug": book.slug})
    return f"{url}?revision={book.cover_updated_at.timestamp()}"
