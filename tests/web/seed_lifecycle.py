from uuid import uuid4

from apps.access.publication_models import PreparedPublication
from apps.catalog.models import BookSource, GeneratedAsset
from apps.ingestion.models import SourceCatalogEntry
from seed_reader import create_reading_book


def create_lifecycle_fixture(actor):
    books = {}
    for profile in ("chromium", "webkit", "firefox", "android", "ios"):
        book = create_reading_book(actor)
        source = f"https://source.example.test/books/lifecycle/{uuid4()}/"
        SourceCatalogEntry.objects.create(
            source_url=source,
            title=book["title"],
            normalized_title=book["title"],
            normalized_display=book["title"],
            catalog_book_id=book["id"],
        )
        BookSource.objects.create(
            book_id=book["id"], source_url=source, normalized_source_url=source
        )
        books[profile] = book
    return books


def create_reader_update_fixture(actor):
    books = {}
    for profile in ("chromium", "webkit", "firefox", "android", "ios"):
        book = create_reading_book(actor)
        asset = GeneratedAsset.objects.get(book_id=book["id"], asset_type="epub")
        publication = PreparedPublication.objects.get(checksum=asset.checksum)
        publication.manifest.pop("manifest_version")
        publication.save(update_fields=["manifest"])
        books[profile] = book
    return books
