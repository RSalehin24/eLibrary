from pathlib import Path

import pytest
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
)
from apps.ingestion.models import (
    BookSubmission,
    JobStatus,
    ProcessingJob,
    SubmissionStatus,
)
from apps.ingestion.services.submissions import (
    process_submission_job,
)


@pytest.mark.django_db
def test_process_submission_job_persists_metadata_and_assets(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.retry_and_deduplication.capture_source_page_metadata",
        lambda source_url: None,
    )
    user = User.objects.create_user(
        email="processor@example.com", password="strong-password-123"
    )
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/test-book/",
        normalized_input="test book",
        resolved_url="https://www.example.com/books/test-book/",
        resolution_status="resolved",
        resolution_confidence=1.0,
        status="queued",
    )
    job = ProcessingJob.objects.create(submission=submission)

    sample = {
        "book_title": "টেস্ট বুক",
        "author": "লেখক এক, লেখক দুই",
        "series": "রহস্য সিরিজ, সংগ্রহ",
        "book_type": "রহস্য, উপন্যাস",
        "cover": "book_cover.jpg",
        "main_content": "<p>মূল অংশ</p>",
        "book_info": "<p>অনুবাদ: অনুবাদক এক</p><p>সম্পাদক: সম্পাদক এক</p>",
        "dedication": "<p>উৎসর্গ</p>",
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
    generated_payload = {}

    def fake_scrape_book(url):
        return sample

    def fake_generate_exports(book_data):
        generated_payload.update(book_data)
        output_dir = Path(book_data["output_folder"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "book.html").write_text(
            "<html><body>book</body></html>", encoding="utf-8"
        )
        (output_dir / "টেস্ট বুক.epub").write_bytes(b"epub-bytes")
        (output_dir / "book_cover.jpg").write_bytes(b"cover-bytes")

    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.scrape_book",
        fake_scrape_book,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.generate_exports",
        fake_generate_exports,
    )

    processed_job = process_submission_job(str(job.id))
    submission.refresh_from_db()

    assert processed_job.status == JobStatus.SUCCEEDED
    assert submission.status == SubmissionStatus.READY
    assert Book.objects.count() == 1

    book = Book.objects.get()
    contributor_roles = {
        (relation.contributor.name, relation.role)
        for relation in book.book_contributors.all()
    }
    assert ("লেখক এক", "author") in contributor_roles
    assert ("লেখক দুই", "author") in contributor_roles
    assert ("অনুবাদক এক", "translator") in contributor_roles
    assert ("সম্পাদক এক", "editor") in contributor_roles
    assert book.dedication_html == ""
    assert book.content_items == sample["content_items"]
    assert generated_payload["book_title"] == book.title
    assert generated_payload["dedication"] == book.dedication_html
    assert generated_payload["content_items"] == book.content_items
    assert book.generated_assets.filter(asset_type=GeneratedAssetType.HTML).exists()
    assert book.generated_assets.filter(asset_type=GeneratedAssetType.EPUB).exists()
    assert book.generated_assets.filter(asset_type=GeneratedAssetType.COVER).exists()


@pytest.mark.django_db
def test_process_submission_job_resolves_cover_asset_when_scraped_extension_is_wrong(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.retry_and_deduplication.capture_source_page_metadata",
        lambda source_url: None,
    )
    user = User.objects.create_user(
        email="processor-cover@example.com", password="strong-password-123"
    )
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/test-cover-book/",
        normalized_input="test cover book",
        resolved_url="https://www.example.com/books/test-cover-book/",
        resolution_status="resolved",
        resolution_confidence=1.0,
        status="queued",
    )
    job = ProcessingJob.objects.create(submission=submission)

    sample = {
        "book_title": "কভার টেস্ট বুক",
        "author": "লেখক এক",
        "series": "",
        "book_type": "",
        "cover": "book_image.hpg",
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

    def fake_scrape_book(url):
        return sample

    def fake_generate_exports(book_data):
        output_dir = Path(book_data["output_folder"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "book.html").write_text(
            "<html><body><img src='book_image.hpg' alt='Book Cover'></body></html>",
            encoding="utf-8",
        )
        (output_dir / "কভার টেস্ট বুক.epub").write_bytes(b"epub-bytes")
        (output_dir / "book_cover.jpg").write_bytes(b"cover-bytes")

    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.scrape_book",
        fake_scrape_book,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.generate_exports",
        fake_generate_exports,
    )

    process_submission_job(str(job.id))

    cover_asset = GeneratedAsset.objects.get(asset_type=GeneratedAssetType.COVER)
    assert cover_asset.status == GeneratedAssetStatus.READY
    assert cover_asset.legacy_path == ""


@pytest.mark.django_db
def test_process_submission_job_keeps_only_media_copies_of_generated_assets(
    tmp_path, settings, monkeypatch
):
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.retry_and_deduplication.capture_source_page_metadata",
        lambda source_url: None,
    )
    settings.MEDIA_ROOT = tmp_path / "media"

    user = User.objects.create_user(
        email="single-copy@example.com", password="strong-password-123"
    )
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/single-copy-book/",
        normalized_input="single copy book",
        resolved_url="https://www.example.com/books/single-copy-book/",
        resolution_status="resolved",
        resolution_confidence=1.0,
        status="queued",
    )
    job = ProcessingJob.objects.create(submission=submission)
    output_dir = tmp_path / "legacy-output"

    sample = {
        "book_title": "একক কপি বই",
        "author": "লেখক এক",
        "series": "",
        "book_type": "",
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
        "output_folder": str(output_dir),
    }

    def fake_scrape_book(url):
        return sample

    def fake_generate_exports(book_data):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "book.html").write_text(
            "<html><body>book</body></html>", encoding="utf-8"
        )
        (output_dir / "একক কপি বই.epub").write_bytes(b"epub-bytes")
        (output_dir / "book_cover.jpg").write_bytes(b"cover-bytes")

    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.scrape_book",
        fake_scrape_book,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.generate_exports",
        fake_generate_exports,
    )

    process_submission_job(str(job.id))

    book = Book.objects.get()
    media_dir = Path(settings.MEDIA_ROOT) / "generated" / book.slug
    saved_names = sorted(path.name for path in media_dir.iterdir())
    assert "book.html" in saved_names
    assert "book_cover.jpg" in saved_names
    assert len([name for name in saved_names if name.endswith(".epub")]) == 1
    assert len(saved_names) == 3
    assert not output_dir.exists()

    for asset in book.generated_assets.order_by("asset_type"):
        assert asset.legacy_path == ""
        assert asset.file
