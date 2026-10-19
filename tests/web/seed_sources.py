from apps.access.models import PermissionGrant, PermissionScope
from apps.catalog.models import BookSource
from apps.ingestion.models import SourceCatalogEntry
from django.utils import timezone
from seed_source_media import create_source_media


def create_source_fixture(identity, reading_book):
    create_source_media(reading_book)
    entries = [
        SourceCatalogEntry.objects.create(
            source_url=f"https://source.example.test/books/{identity}/{number}/",
            title=f"আবিষ্কৃত বই {identity} {number}",
            author_line="পরীক্ষার লেখক",
            normalized_title=f"আবিষ্কৃত বই {identity} {number}",
            normalized_display=f"আবিষ্কৃত বই {identity} {number} পরীক্ষার লেখক",
            raw_data={
                "cookie": "private-source-fixture",
                "html": "private-source-body",
            },
        )
        for number in range(51)
    ]
    BookSource.objects.create(
        book_id=reading_book["id"],
        source_url=entries[0].source_url,
        normalized_source_url=entries[0].source_url,
    )
    entries[0].raw_data = {
        **entries[0].raw_data,
        "source_unfinished": True,
        "source_update": {
            "status": "available",
            "checked_at": timezone.now().isoformat(),
            "chapter_count": 2,
            "published_chapter_count": 1,
            "source_modified_at": None,
        },
    }
    entries[0].save(update_fields=["raw_data"])
    return {
        "query": identity,
        "linked": {"id": str(entries[0].pk), "title": entries[0].title},
        "unlinked": {"id": str(entries[1].pk), "title": entries[1].title},
    }


def grant_source_processing(user):
    PermissionGrant.objects.create(user=user, scope=PermissionScope.PROCESSING_MANAGE)
