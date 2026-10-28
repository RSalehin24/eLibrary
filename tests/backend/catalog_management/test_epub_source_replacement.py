import pytest
from apps.catalog.models import BookSource, GeneratedAsset
from apps.ingestion.models import SourceCatalogEntry, SourceEdition
from apps.ingestion.source_processing.classification import VALIDATOR_VERSION
from apps.ingestion.source_processing.storage import write_artifact
from apps.processing.job_models import BackgroundJob
from django.utils import timezone

from ..access.reader_fixtures import write_epub
from .epub_upload_fixtures import send_upload

pytestmark = pytest.mark.django_db

BODY_ONE = "<h1>প্রথম অধ্যায়</h1><p>বাংলা বইয়ের প্রথম পাতা।</p>"
BODY_TWO = "<h1>দ্বিতীয় অধ্যায়</h1><p>শেষ পাতা।</p>"


@pytest.fixture
def source_edition(upload_book):
    actor, book, _, _ = upload_book
    book.source_quality_state = "verified"
    book.save()
    BookSource.objects.create(
        book=book,
        source_url="https://www.example.com/books/proven/",
        normalized_source_url="https://www.example.com/books/proven/",
    )
    source = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/proven/",
        title=book.title,
        catalog_book=book,
    )
    operation = BackgroundJob.objects.create(
        requested_by=actor,
        book=book,
        source_record=source,
        kind="process_source",
        state="succeeded",
        available_at=timezone.now(),
    )
    reference = write_artifact(
        operation.pk,
        {
            "document": {
                "sections": [
                    {"section_type": "body", "html": BODY_ONE},
                    {"section_type": "body", "html": BODY_TWO},
                ]
            }
        },
    )
    return SourceEdition.objects.create(
        book=book,
        source=source,
        operation=operation,
        state="published",
        validator_version=VALIDATOR_VERSION,
        document_reference=reference,
        validation_report={"verified": True},
    )


def test_source_upload_matches_every_retained_verified_reading_chapter(
    upload_book, source_edition
):
    response = send_upload(upload_book)
    assert response.status_code == 200
    assert response.json()["state"] == "published"
    assert (
        GeneratedAsset.objects.get(book=upload_book[1], asset_type="epub").status
        == "ready"
    )


@pytest.mark.parametrize("hide_in_archive", [False, True])
def test_missing_reading_text_cannot_hide_in_an_unread_archive_resource(
    upload_book, source_edition, hide_in_archive
):
    changes = {"OEBPS/chapter-2.xhtml": "<html><p>A different chapter.</p></html>"}
    if hide_in_archive:
        changes["OEBPS/not-in-reading-order.xhtml"] = BODY_TWO
    write_epub(upload_book[3], changes)
    response = send_upload(upload_book)
    assert response.status_code == 400
    assert (
        "every verified website chapter" in response.json()["field_errors"]["file"][0]
    )
    assert not GeneratedAsset.objects.exists()


@pytest.mark.parametrize("quality", ["unchecked", "quarantined"])
def test_source_upload_cannot_clear_unverified_or_quarantined_quality(
    upload_book, source_edition, quality
):
    book = upload_book[1]
    book.source_quality_state = quality
    book.save()
    response = send_upload(upload_book)
    assert response.status_code == 409 and "Regenerate" in response.json()["detail"]
    book.refresh_from_db()
    assert book.source_quality_state == quality
    assert not GeneratedAsset.objects.exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("validator_version", 0),
        ("validation_report", {"verified": False}),
        ("state", "quarantined"),
        ("document_reference", "00000000-0000-0000-0000-000000000000"),
    ],
)
def test_source_upload_requires_current_complete_retained_evidence(
    upload_book, source_edition, field, value
):
    setattr(source_edition, field, value)
    source_edition.save()
    assert send_upload(upload_book).status_code == 409
    assert not GeneratedAsset.objects.exists()


def test_source_upload_cannot_replace_legacy_books_without_edition_evidence(
    upload_book,
):
    book = upload_book[1]
    BookSource.objects.create(
        book=book,
        source_url="https://www.example.com/books/legacy/",
        normalized_source_url="https://www.example.com/books/legacy/",
    )
    assert send_upload(upload_book).status_code == 409
    assert not GeneratedAsset.objects.exists()
