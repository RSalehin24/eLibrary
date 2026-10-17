from uuid import uuid4

from apps.catalog.models import Book, BookContributor, BookSource, Contributor
from apps.ingestion.source_processing.regeneration import request_book_regeneration
from django.utils import timezone

from tests.backend.access.reader_fixtures import prepared_asset


def create_regeneration_fixture(source_job, folder):
    book = Book.objects.create(
        title="সম্পাদিত বইয়ের নাম",
        summary="সম্পাদিত পরিচিতি",
        seo_title="Edited SEO",
        state="published",
        review_state="approved",
        editorial_reviewed_at=timezone.now(),
        main_content_html="<p>Previous text</p>",
    )
    author = Contributor.objects.create(name="সম্পাদিত লেখক")
    BookContributor.objects.create(book=book, contributor=author)
    entry = source_job.source_record
    entry.catalog_book = book
    entry.save()
    BookSource.objects.create(
        book=book, source_url=entry.source_url, normalized_source_url=entry.source_url
    )
    source_job.state = "cancelled"
    source_job.save()
    asset, publication = prepared_asset(book, folder)
    return source_job.requested_by, book, entry, asset, publication


def request_regeneration(fixture):
    actor, book, _, _, _ = fixture
    return request_book_regeneration(
        actor,
        book.pk,
        {"operation_id": uuid4(), "expected_updated_at": book.updated_at},
    )
