from pathlib import Path

import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, BookContributor, Category, Contributor
from apps.ingestion.models import (
    BookSubmission,
    ProcessingJob,
    ResolutionStatus,
    SubmissionStatus,
)
from apps.ingestion.services.legacy_adapter import normalize_source_url, normalize_text
from apps.ingestion.services.submissions import (
    find_exact_existing_book,
    process_submission_job,
)


@pytest.mark.django_db
def test_find_exact_existing_book_requires_author_overlap_for_same_title():
    existing_book = Book.objects.create(
        title="শ্রেষ্ঠ কবিতা", source_site="example.com", state="ready"
    )
    existing_author = Contributor.objects.create(name="কবি এক")
    existing_category = Category.objects.create(name="কবিতা")
    BookContributor.objects.create(
        book=existing_book, contributor=existing_author, role="author"
    )
    existing_book.book_categories.model.objects.create(
        book=existing_book,
        category=existing_category,
        raw_value=existing_category.name,
    )

    matched = find_exact_existing_book(
        {"book_title": "শ্রেষ্ঠ কবিতা", "author": "কবি দুই", "book_type": "কবিতা"}
    )
    assert matched is None

    matched_same_author = find_exact_existing_book(
        {"book_title": "শ্রেষ্ঠ কবিতা", "author": "কবি এক", "book_type": "কবিতা"}
    )
    assert matched_same_author is not None
    assert matched_same_author.id == existing_book.id


@pytest.mark.django_db
def test_process_submission_job_reuses_source_identity_created_during_scraping(
    tmp_path,
    monkeypatch,
):
    user = User.objects.create_user(
        email="unique-conflict@example.com", password="strong-password-123"
    )
    source_url = "https://www.example.com/books/unique-conflict-book/"
    existing_book = Book.objects.create(
        title="শ্রেষ্ঠ কবিতা", source_site="example.com", state="ready"
    )
    existing_author = Contributor.objects.create(name="কবি এক")
    existing_category = Category.objects.create(name="কবিতা")
    BookContributor.objects.create(
        book=existing_book, contributor=existing_author, role="author"
    )
    existing_book.book_categories.model.objects.create(
        book=existing_book,
        category=existing_category,
        raw_value=existing_category.name,
    )
    lookup_calls = {"count": 0}
    normalized_source_url = normalize_source_url(source_url)

    def staged_source_url_lookup(normalized_url):
        lookup_calls["count"] += 1
        if lookup_calls["count"] == 1:
            return None
        if normalized_url == normalized_source_url:
            return existing_book
        return None

    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.find_existing_book_by_source_url",
        staged_source_url_lookup,
    )

    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input=source_url,
        normalized_input=normalize_text(source_url),
        resolved_url=source_url,
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_confidence=1.0,
        status=SubmissionStatus.QUEUED,
    )
    job = ProcessingJob.objects.create(submission=submission)

    sample = {
        "book_title": "শ্রেষ্ঠ কবিতা",
        "author": "কবি দুই",
        "book_type": "গল্প",
        "series": "",
        "cover": "book_cover.jpg",
        "main_content": "<p>মূল অংশ</p>",
        "book_info": "",
        "dedication": "",
        "toc": [{"title": "অধ্যায় ১", "type": "lesson", "has_content": True}],
        "content_items": [
            {
                "title": "অধ্যায় ১",
                "content": "<p>বিষয়বস্তু</p>",
                "type": "lesson",
                "parent": None,
            }
        ],
        "output_folder": str(tmp_path),
    }

    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.retry_and_deduplication.capture_source_page_metadata",
        lambda _url: None,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.scrape_book",
        lambda _url: sample,
    )

    def fake_generate_exports(book_data):
        output_dir = Path(book_data["output_folder"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "book.html").write_text(
            "<html><body>book</body></html>", encoding="utf-8"
        )
        (output_dir / "শ্রেষ্ঠ কবিতা.epub").write_bytes(b"epub-bytes")
        (output_dir / "book_cover.jpg").write_bytes(b"cover-bytes")

    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.generate_exports",
        fake_generate_exports,
    )

    process_submission_job(str(job.id))
    submission.refresh_from_db()

    assert lookup_calls["count"] >= 2
    assert submission.status == SubmissionStatus.READY
    assert submission.linked_book_id == existing_book.id
