import pytest
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookSource,
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
)
from apps.common.models import LifecycleState
from apps.ingestion.models import (
    BookSubmission,
    JobStatus,
    ProcessingJob,
    SourceCatalogEntry,
    SubmissionOrigin,
    SubmissionStatus,
)
from apps.ingestion.services.legacy_adapter import normalize_text
from django.utils import timezone


@pytest.mark.django_db
def test_source_catalog_entries_apply_status_filter_before_pagination_and_return_counts(
    client,
):
    admin = User.objects.create_superuser(
        email="catalog-filter@example.com", password="strong-password-123"
    )
    client.force_login(admin)

    ready_book = Book.objects.create(title="A Ready Book", state=LifecycleState.READY)
    BookSource.objects.create(
        book=ready_book,
        source_url="https://www.example.com/books/ready-book/",
        normalized_source_url="https://www.example.com/books/ready-book/",
    )
    GeneratedAsset.objects.create(
        book=ready_book,
        asset_type=GeneratedAssetType.HTML,
        status=GeneratedAssetStatus.READY,
    )
    GeneratedAsset.objects.create(
        book=ready_book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
    )

    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/ready-book/",
        title="A Ready Book",
        author_line="Author",
        normalized_title="a ready book",
        normalized_display="a ready book author",
    )
    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/new-book/",
        title="Z New Book",
        author_line="Author",
        normalized_title="z new book",
        normalized_display="z new book author",
    )

    response = client.get("/api/ingestion/catalog/entries/?limit=1&status=new")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 1
    assert payload["summary"]["new"] == 1
    assert payload["pagination"]["total_count"] == 1
    assert payload["pagination"]["page_count"] == 1
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["title"] == "Z New Book"


@pytest.mark.django_db
def test_source_catalog_entries_can_filter_deleted_books(client):
    admin = User.objects.create_superuser(
        email="catalog-deleted-filter@example.com", password="strong-password-123"
    )
    client.force_login(admin)

    deleted_book = Book.objects.create(
        title="Deleted Book", state=LifecycleState.SOFT_DELETED
    )
    Book.objects.filter(pk=deleted_book.pk).update(deleted_at=timezone.now())
    deleted_book.refresh_from_db()
    BookSource.objects.create(
        book=deleted_book,
        source_url="https://www.example.com/books/deleted-book/",
        normalized_source_url="https://www.example.com/books/deleted-book/",
    )
    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/deleted-book/",
        title="Deleted Book",
        author_line="Writer",
        normalized_title="deleted book",
        normalized_display="deleted book writer",
    )
    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/new-book/",
        title="New Book",
        author_line="Writer",
        normalized_title="new book",
        normalized_display="new book writer",
    )

    response = client.get("/api/ingestion/catalog/entries/?limit=1&status=deleted")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 1
    assert payload["summary"]["deleted"] == 1
    assert payload["pagination"]["total_count"] == 1
    assert payload["pagination"]["page_count"] == 1
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["title"] == "Deleted Book"
    assert payload["entries"][0]["curation_status"] == "deleted"


@pytest.mark.django_db
def test_source_catalog_entries_summary_reports_queued_and_processing_separately(
    client,
):
    admin = User.objects.create_superuser(
        email="catalog-summary@example.com", password="strong-password-123"
    )
    client.force_login(admin)

    queued_book = Book.objects.create(title="Queued Book")
    queued_source_url = "https://www.example.com/books/queued-book/"
    BookSource.objects.create(
        book=queued_book,
        source_url=queued_source_url,
        normalized_source_url=queued_source_url,
    )
    queued_submission = BookSubmission.objects.create(
        submitter=admin,
        input_type="url",
        original_input=queued_source_url,
        normalized_input="queued book",
        resolved_url=queued_source_url,
        origin=SubmissionOrigin.CURATION,
        status=SubmissionStatus.QUEUED,
    )
    ProcessingJob.objects.create(
        submission=queued_submission,
        book=queued_book,
        status=JobStatus.QUEUED,
    )

    processing_book = Book.objects.create(title="Processing Book")
    processing_source_url = "https://www.example.com/books/processing-book/"
    BookSource.objects.create(
        book=processing_book,
        source_url=processing_source_url,
        normalized_source_url=processing_source_url,
    )
    processing_submission = BookSubmission.objects.create(
        submitter=admin,
        input_type="url",
        original_input=processing_source_url,
        normalized_input="processing book",
        resolved_url=processing_source_url,
        origin=SubmissionOrigin.CURATION,
        status=SubmissionStatus.PROCESSING,
    )
    ProcessingJob.objects.create(
        submission=processing_submission,
        book=processing_book,
        status=JobStatus.PROCESSING,
    )

    SourceCatalogEntry.objects.create(
        source_url=queued_source_url,
        title="Queued Book",
        author_line="Writer",
        normalized_title=normalize_text("Queued Book"),
        normalized_display=normalize_text("Queued Book Writer"),
    )
    SourceCatalogEntry.objects.create(
        source_url=processing_source_url,
        title="Processing Book",
        author_line="Writer",
        normalized_title=normalize_text("Processing Book"),
        normalized_display=normalize_text("Processing Book Writer"),
    )

    response = client.get("/api/ingestion/catalog/entries/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["queued"] == 1
    assert payload["summary"]["processing"] == 1


@pytest.mark.django_db
def test_source_catalog_entries_support_lightweight_browse_without_summary_or_sync_state(
    client,
):
    admin = User.objects.create_superuser(
        email="catalog-lightweight@example.com", password="strong-password-123"
    )
    client.force_login(admin)

    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/b-title/",
        title="B Title",
        author_line="Writer",
        normalized_title="b title",
        normalized_display="b title writer",
    )
    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/a-title/",
        title="A Title",
        author_line="Writer",
        normalized_title="a title",
        normalized_display="a title writer",
    )

    response = client.get(
        "/api/ingestion/catalog/entries/?include_summary=0&include_sync_state=0&sort=title_asc&limit=1"
    )

    assert response.status_code == 200
    payload = response.json()
    assert "summary" not in payload
    assert "sync_state" not in payload
    assert payload["pagination"]["total_count"] == 2
    assert payload["pagination"]["page_count"] == 2
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["title"] == "A Title"
