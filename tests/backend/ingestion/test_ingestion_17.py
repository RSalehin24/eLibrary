import json

import pytest
from apps.access.models import PreviewAccessSession
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookSource,
)
from apps.ingestion.models import (
    BookSubmission,
    ProcessingJob,
    ResolutionStatus,
    SourceCatalogEntry,
    SubmissionStatus,
)
from apps.ingestion.services.legacy_adapter import normalize_text


@pytest.mark.django_db
def test_duplicate_review_list_defaults_to_pending_reviews(client):
    from apps.accounts.models import User
    from apps.catalog.models import Book

    actor = User.objects.create_user(email="removed-review@example.test", is_staff=True)
    book = Book.objects.create(title="অপ্রকাশিত বই")
    client.force_login(actor)
    assert client.get("/api/ingestion/duplicate-reviews/").status_code == 404
    assert (
        client.post(f"/api/ingestion/duplicate-reviews/{book.pk}/resolve/").status_code
        == 404
    )
    book.refresh_from_db()
    assert book.state == "draft"


@pytest.mark.django_db
def test_duplicate_review_keep_new_queues_recreate_for_deleted_existing_book(client):
    from apps.accounts.models import User
    from apps.catalog.models import Book

    actor = User.objects.create_user(email="removed-review@example.test", is_staff=True)
    book = Book.objects.create(title="অপ্রকাশিত বই")
    client.force_login(actor)
    assert client.get("/api/ingestion/duplicate-reviews/").status_code == 404
    assert (
        client.post(f"/api/ingestion/duplicate-reviews/{book.pk}/resolve/").status_code
        == 404
    )
    book.refresh_from_db()
    assert book.state == "draft"


@pytest.mark.django_db
def test_public_submission_accepts_mixed_entries_and_reuses_existing_books(
    client, monkeypatch
):
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.retry_and_deduplication.capture_source_page_metadata",
        lambda source_url: None,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.resolution.TitleResolver.refresh_catalog",
        lambda *args, **kwargs: None,
    )
    existing_book = Book.objects.create(title="সংরক্ষিত বই", state="ready")
    BookSource.objects.create(
        book=existing_book,
        source_url="https://www.example.com/books/existing-book/",
        normalized_source_url="https://www.example.com/books/existing-book/",
        source_title="সংরক্ষিত বই",
    )

    response = client.post(
        "/api/ingestion/submissions/",
        data=json.dumps(
            {
                "entries": [
                    "https://www.example.com/books/existing-book/",
                    "সংরক্ষিত বই",
                ],
                "auto_process": True,
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert len(payload) == 2
    reused_entry = next(entry for entry in payload if entry["input_type"] == "url")
    title_entry = next(entry for entry in payload if entry["input_type"] == "title")

    assert reused_entry["served_from_database"] is True
    assert reused_entry["linked_book_slug"] == existing_book.slug
    assert title_entry["served_from_database"] is False
    assert title_entry["linked_book_slug"] == ""
    assert title_entry["status"] == "failed"
    assert PreviewAccessSession.objects.count() == 0


@pytest.mark.django_db
def test_ambiguous_title_fails_without_manual_confirmation(client, monkeypatch):
    user = User.objects.create_user(
        email="reviewer@example.com", password="strong-password-123"
    )
    client.force_login(user)

    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/sample-book-one/",
        title="স্যাম্পল বুক এক",
        author_line="লেখক",
        normalized_title=normalize_text("স্যাম্পল বুক এক"),
        normalized_display=normalize_text("স্যাম্পল বুক এক লেখক"),
    )
    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/sample-book-two/",
        title="স্যাম্পল বুক দুই",
        author_line="লেখক",
        normalized_title=normalize_text("স্যাম্পল বুক দুই"),
        normalized_display=normalize_text("স্যাম্পল বুক দুই লেখক"),
    )

    created = client.post(
        "/api/ingestion/submissions/",
        data=json.dumps(
            {
                "input_type": "title",
                "content": "স্যাম্পল বুক",
                "auto_process": False,
            }
        ),
        content_type="application/json",
    )
    assert created.status_code == 201
    payload = created.json()[0]
    assert payload["status"] == "failed"
    assert len(payload["candidates"]) == 2

    confirm = client.post(
        f"/api/ingestion/submissions/{payload['id']}/confirm-candidate/",
        data=json.dumps({"candidate_id": payload["candidates"][0]["id"]}),
        content_type="application/json",
    )
    assert confirm.status_code == 404
    submission = BookSubmission.objects.get(pk=payload["id"])
    assert submission.status == SubmissionStatus.FAILED
    assert submission.resolution_status == ResolutionStatus.AMBIGUOUS
    assert not ProcessingJob.objects.filter(submission=submission).exists()
