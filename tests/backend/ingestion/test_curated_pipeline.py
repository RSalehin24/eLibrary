import json
from copy import deepcopy
from io import StringIO
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.core.management import call_command

from apps.catalog.models import (
    CuratedBookDocument,
    CuratedDocumentStatus,
    CuratedEntity,
    CuratedSection,
    GeneratedAsset,
)
from apps.common.models import LifecycleState, ReviewState
from apps.ingestion.pipeline import book_manifest
from apps.ingestion.pipeline.book_manifest import build_manifest_from_legacy_payload
from apps.ingestion.management.commands.curate_ebangla_books import verify_curated_result
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline.curated_persistence import persist_curated_book
from apps.ingestion.pipeline.curated_pipeline import curate_book_document
from apps.ingestion.pipeline.curated_validation import source_chrome_hits, validate_document
from apps.ingestion.services.legacy_adapter import generate_exports


def fake_scraped_payload(tmp_path, *, content_items=None):
    return {
        "book_title": "সোফির জগৎ",
        "author": "ইয়স্তেন গার্ডার",
        "series": "দর্শন সিরিজ",
        "book_type": "উপন্যাস",
        "cover": "",
        "main_content": "",
        "book_info": """
        <p>অনুবাদ : জি. এইচ. হাবীব</p>
        <p>প্রকাশক : ঐতিহ্য</p>
        <p>প্রথম সংস্করণ: বৈশাখ ১৩৮২</p>
        <p>মূল : Sophie's World</p>
        """,
        "dedication": "<p>পাঠকদের জন্য</p>",
        "front_sections": [{"title": "ভূমিকা", "html": "<p>ভূমিকা লেখা</p>"}],
        "back_sections": [{"title": "পরিশিষ্ট", "html": "<p>শেষ কথা</p>"}],
        "toc": [],
        "content_items": content_items
        if content_items is not None
        else [
            {
                "title": "প্রথম অধ্যায়",
                "content": "<p>মূল লেখা</p>",
                "type": "lesson",
                "parent": None,
                "path": ["প্রথম অধ্যায়"],
            }
        ],
        "output_folder": str(tmp_path),
    }


def patch_scraper(monkeypatch, payload):
    def fake_manifest_builder(url, **kwargs):
        source_pages = build_manifest_from_legacy_payload(
            url,
            {**payload, "called_url": url, "called_kwargs": kwargs},
        )
        return source_pages

    monkeypatch.setattr(
        "apps.ingestion.pipeline.curated_source.build_manifest_source_pages",
        fake_manifest_builder,
    )


def test_curated_document_extracts_entities_sections_and_generated_toc(monkeypatch, tmp_path):
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path))

    curated = curate_book_document("https://ebanglalibrary.com/books/sophie/")
    document = curated["document"]

    assert document["status"] == CuratedDocumentStatus.VALIDATED
    assert document["structure_type"] == "flat_toc"
    assert document["projection"]["toc"][0]["title"] == "প্রথম অধ্যায়"
    roles = {(entity["role"], entity["value"]) for entity in document["entities"]}
    assert ("translator", "জি. এইচ. হাবীব") in roles
    assert ("publisher", "ঐতিহ্য") in roles
    assert ("edition", "বৈশাখ ১৩৮২") in roles
    section_types = [section["section_type"] for section in document["sections"]]
    assert section_types == [
        "title_page",
        "book_info",
        "dedication",
        "front_matter",
        "generated_toc",
        "body",
        "back_matter",
    ]


def test_curated_document_routes_structural_failures_to_review(monkeypatch, tmp_path):
    duplicate_items = [
        {
            "title": "এক",
            "content": "<p>প্রথম লেখা</p>",
            "type": "lesson",
            "parent": None,
            "path": ["এক"],
        },
        {
            "title": "এক",
            "content": "<p>দ্বিতীয় লেখা</p>",
            "type": "lesson",
            "parent": None,
            "path": ["এক"],
        },
    ]
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path, content_items=duplicate_items))

    curated = curate_book_document("https://www.ebanglalibrary.com/books/duplicate/")

    assert curated["status"] == CuratedDocumentStatus.REVIEW_REQUIRED
    assert "Duplicate content path: এক." in curated["validation"]["errors"]


def test_source_chrome_detection_does_not_match_inside_bangla_words():
    sections = [
        {
            "section_id": "body",
            "section_type": "body",
            "html": "<p>আমি প্রাসঙ্গিক বইপত্র পড়তে লাগলাম।</p>",
        }
    ]

    assert source_chrome_hits(sections) == []


def test_source_chrome_detection_matches_related_books_label():
    sections = [
        {
            "section_id": "body",
            "section_type": "body",
            "html": "<p>প্রাসঙ্গিক বই</p><p>অন্য বইয়ের নাম</p>",
        }
    ]

    assert source_chrome_hits(sections) == [
        {"section_id": "body", "pattern": "প্রাসঙ্গিক বই"}
    ]


def test_source_chrome_detection_allows_comment_phrase_inside_prose():
    sections = [
        {
            "section_id": "body",
            "section_type": "body",
            "html": "<p>সরকার আশা করছে না, আপনি আর কোন মন্তব্য করুন। একটু থামলো সে।</p>",
        }
    ]

    assert source_chrome_hits(sections) == []


def test_curated_validation_rejects_partial_source_fetches(monkeypatch, tmp_path):
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path))
    curated = curate_book_document("https://www.ebanglalibrary.com/books/partial/")
    document = curated["document"]
    snapshot = {
        **curated["source_snapshot"],
        "pages": [
            {
                "url": "https://www.ebanglalibrary.com/books/partial/",
                "kind": "landing",
                "status": "fetched",
                "status_code": 200,
            },
            {
                "url": "https://www.ebanglalibrary.com/books/partial/chapter/",
                "kind": "lesson",
                "status": "failed",
                "status_code": 404,
            },
        ],
    }

    validation = validate_document(document, snapshot)

    assert validation["status"] == CuratedDocumentStatus.REVIEW_REQUIRED
    assert validation["errors"] == [
        "Source page was not fetched: https://www.ebanglalibrary.com/books/partial/chapter/ (404)."
    ]


def test_curated_validation_rejects_empty_discovered_toc_leaf(monkeypatch, tmp_path):
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path))
    curated = curate_book_document("https://www.ebanglalibrary.com/books/empty-leaf/")
    document = deepcopy(curated["document"])
    document["projection"]["toc"] = [
        {
            "title": "শূন্য অধ্যায়",
            "type": "lesson",
            "has_content": False,
            "path": ["শূন্য অধ্যায়"],
            "source_url": "https://www.ebanglalibrary.com/books/empty-leaf/chapter/",
        }
    ]
    document["projection"]["content_items"] = []

    validation = validate_document(document, curated["source_snapshot"])

    assert validation["status"] == CuratedDocumentStatus.REVIEW_REQUIRED
    assert "TOC content leaf has no extracted body: শূন্য অধ্যায়." in validation["errors"]


@pytest.mark.django_db
def test_curated_persistence_writes_document_evidence_and_projection(monkeypatch, tmp_path):
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path))
    source_url = "https://www.ebanglalibrary.com/books/sophie/"
    curated = curate_book_document(source_url)

    book, curated_document = persist_curated_book(curated, source_url=source_url)

    assert book.title == "সোফির জগৎ"
    assert book.state == LifecycleState.READY
    assert book.review_state == ReviewState.PENDING
    assert book.raw_scrape_payload["curated_document_model_id"] == str(curated_document.id)
    assert "content_items" not in book.raw_scrape_payload
    assert book.raw_scrape_payload["content_summary"]["content_item_count"] == 1
    assert book.content_items[0]["content"] == "<p>মূল লেখা</p>"
    assert curated_document.document["projection"]["content_summary"]["content_item_count"] == 1
    assert all("html" not in section for section in curated_document.document["sections"])
    assert CuratedBookDocument.objects.count() == 1
    assert CuratedEntity.objects.filter(document=curated_document, role="translator").exists()
    assert CuratedSection.objects.filter(document=curated_document, section_type="body").exists()


@pytest.mark.django_db
def test_curated_result_verification_catches_persisted_content_mismatch(monkeypatch, tmp_path):
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path))
    source_url = "https://www.ebanglalibrary.com/books/sophie/"
    curated = curate_book_document(source_url)
    book, curated_document = persist_curated_book(curated, source_url=source_url)

    book.content_items = []

    assert "Persisted content_items do not match projection." in verify_curated_result(
        curated,
        book=book,
        curated_document=curated_document,
    )


@pytest.mark.django_db
def test_curate_command_skips_existing_curated_source(monkeypatch, tmp_path):
    source_url = "https://www.ebanglalibrary.com/books/sophie/"
    SourceCatalogEntry.objects.create(
        source_url=source_url,
        title="সোফির জগৎ",
        normalized_title="সোফির জগৎ",
        normalized_display="সোফির জগৎ",
    )
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path))
    curated = curate_book_document(source_url)
    persist_curated_book(curated, source_url=source_url)

    def fail_if_called(_source_url):
        raise AssertionError("Existing curated sources should be skipped")

    monkeypatch.setattr(
        "apps.ingestion.management.commands.curate_ebangla_books.curate_book_document",
        fail_if_called,
    )
    report_path = tmp_path / "skip-report.json"

    call_command(
        "curate_ebangla_books",
        "--offset",
        "0",
        "--batch-size",
        "1",
        "--skip-existing",
        "--report-path",
        str(report_path),
        stdout=StringIO(),
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["processed"] == 0
    assert report["skipped_existing"] == 1
    assert report["results"][0]["skipped"] is True
    assert CuratedBookDocument.objects.count() == 1


@pytest.mark.django_db
def test_curate_command_reports_clean_persisted_verification(monkeypatch, tmp_path):
    source_url = "https://www.ebanglalibrary.com/books/sophie/"
    SourceCatalogEntry.objects.create(
        source_url=source_url,
        title="সোফির জগৎ",
        normalized_title="সোফির জগৎ",
        normalized_display="সোফির জগৎ",
    )
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path))
    report_path = tmp_path / "curation-report.json"

    call_command(
        "curate_ebangla_books",
        "--offset",
        "0",
        "--batch-size",
        "1",
        "--report-path",
        str(report_path),
        stdout=StringIO(),
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = report["results"][0]
    assert report["processed"] == 1
    assert report["validated"] == 1
    assert report["verified"] == 1
    assert report["verification_failures"] == 0
    assert result["verification_errors"] == []
    assert result["book_id"]
    assert result["curated_document_id"]


@pytest.mark.django_db
def test_curate_command_can_require_validated_documents(monkeypatch, tmp_path):
    source_url = "https://www.ebanglalibrary.com/books/review/"
    SourceCatalogEntry.objects.create(
        source_url=source_url,
        title="রিভিউ বই",
        normalized_title="রিভিউ বই",
        normalized_display="রিভিউ বই",
    )
    duplicate_items = [
        {"title": "এক", "content": "<p>প্রথম</p>", "type": "lesson", "path": ["এক"]},
        {"title": "এক", "content": "<p>দ্বিতীয়</p>", "type": "lesson", "path": ["এক"]},
    ]
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path, content_items=duplicate_items))
    report_path = tmp_path / "require-validated-report.json"

    call_command(
        "curate_ebangla_books",
        "--offset",
        "0",
        "--batch-size",
        "1",
        "--require-validated",
        "--continue-on-error",
        "--report-path",
        str(report_path),
        stdout=StringIO(),
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["processed"] == 1
    assert report["review_required"] == 1
    assert report["failed"] == 1
    assert "Duplicate content path: এক." in report["results"][0]["validation_errors"]
    assert CuratedBookDocument.objects.count() == 0


@pytest.mark.django_db
def test_curate_command_can_require_catalog_metadata_match(monkeypatch, tmp_path):
    source_url = "https://www.ebanglalibrary.com/books/sophie/"
    SourceCatalogEntry.objects.create(
        source_url=source_url,
        title="ভুল বই",
        author_line="ইয়স্তেন গার্ডার",
        normalized_title="ভুল বই",
        normalized_display="ভুল বই ইয়স্তেন গার্ডার",
        raw_data={"category": "উপন্যাস"},
    )
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path))
    report_path = tmp_path / "catalog-match-report.json"

    call_command(
        "curate_ebangla_books",
        "--offset",
        "0",
        "--batch-size",
        "1",
        "--require-catalog-match",
        "--continue-on-error",
        "--report-path",
        str(report_path),
        stdout=StringIO(),
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = report["results"][0]
    assert report["processed"] == 1
    assert report["catalog_mismatches"] == 1
    assert report["blocked"] == 1
    assert "Catalog title mismatch: expected ভুল বই; extracted সোফির জগৎ." in result["catalog_errors"]
    assert CuratedBookDocument.objects.count() == 0


@pytest.mark.django_db
def test_review_required_curated_book_persists_without_assets(monkeypatch, tmp_path):
    duplicate_items = [
        {"title": "এক", "content": "<p>প্রথম</p>", "type": "lesson", "path": ["এক"]},
        {"title": "এক", "content": "<p>দ্বিতীয়</p>", "type": "lesson", "path": ["এক"]},
    ]
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path, content_items=duplicate_items))
    curated = curate_book_document("https://www.ebanglalibrary.com/books/review/")

    book, _curated_document = persist_curated_book(
        curated,
        source_url="https://www.ebanglalibrary.com/books/review/",
    )

    assert book.state == LifecycleState.NEEDS_REVIEW
    assert book.review_state == ReviewState.NEEDS_REVIEW
    assert GeneratedAsset.objects.filter(book=book).count() == 0


def test_generators_accept_curated_document_payload(monkeypatch, tmp_path):
    patch_scraper(monkeypatch, fake_scraped_payload(tmp_path))
    curated = curate_book_document("https://www.ebanglalibrary.com/books/export/")

    generate_exports(curated["document"])

    assert (Path(tmp_path) / "book.html").exists()
    assert (Path(tmp_path) / "সোফির জগৎ.epub").exists()


def test_manifest_parser_preserves_paginated_sectioned_nested_toc():
    source_url = "https://www.ebanglalibrary.com/books/sectioned/"
    landing = BeautifulSoup(
        """
        <div class="ld-item-list ld-lesson-list">
          <div class="ld-item-list-items">
            <div class="ld-item-list-section-heading">
              <div class="ld-lesson-section-heading">প্রথম খণ্ড</div>
            </div>
            <div class="ld-item-list-item ld-item-lesson-item" data-ld-expand-id="101">
              <a class="ld-item-name" href="/books/sectioned/chapter-1/">
                <div class="ld-item-title">অধ্যায় ১</div>
              </a>
              <div id="101-container">
                <div class="ld-table-list-item">
                  <a class="ld-table-list-item-preview" href="/books/sectioned/topic-1/">
                    <span class="ld-topic-title">প্রসঙ্গ ১</span>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="ld-pagination ld-pagination-page-course_content_shortcode"
             data-pager-results='{"total_pages": 2}'></div>
        """,
        "html.parser",
    )
    page_two = BeautifulSoup(
        """
        <div class="ld-item-list ld-lesson-list">
          <div class="ld-item-list-items">
            <div class="ld-item-list-item ld-item-lesson-item">
              <a class="ld-item-name" href="/books/sectioned/chapter-2/">
                <div class="ld-item-title">অধ্যায় ২</div>
              </a>
            </div>
          </div>
        </div>
        """,
        "html.parser",
    )

    class FakeContext:
        def __init__(self):
            self.urls = []

        def fetch_soup(self, url, **_kwargs):
            self.urls.append(url)
            return page_two

    ctx = FakeContext()
    toc_nodes, meta = book_manifest.collect_learndash_toc(
        landing,
        source_url,
        ctx,
        book_manifest.normalize_manifest_limits(),
    )
    toc = book_manifest.assign_paths_to_toc(toc_nodes)

    assert meta["has_paginated_toc"] is True
    assert ctx.urls == [
        "https://www.ebanglalibrary.com/books/sectioned/?ld-courseinfo-lesson-page=2",
        "https://www.ebanglalibrary.com/books/sectioned/chapter-2/",
    ]
    assert toc[0]["title"] == "প্রথম খণ্ড"
    assert [child["title"] for child in toc[0]["children"]] == ["অধ্যায় ১", "অধ্যায় ২"]
    assert toc[0]["children"][0]["children"][0]["path"] == [
        "প্রথম খণ্ড",
        "অধ্যায় ১",
        "প্রসঙ্গ ১",
    ]


def test_manifest_content_fetch_does_not_retain_content_soups():
    class FakeResponse:
        status_code = 200
        headers = {"content-type": "text/html; charset=utf-8"}
        encoding = "utf-8"
        apparent_encoding = "utf-8"
        content = """
        <article>
          <div class="entry-content"><p>অধ্যায়ের লেখা</p></div>
        </article>
        """.encode("utf-8")

    class FakeSession:
        headers = {}

        def get(self, *_args, **_kwargs):
            return FakeResponse()

    ctx = book_manifest.SourceFetchContext(FakeSession(), sleep_seconds=0)
    item = book_manifest.fetch_content_item(
        {
            "title": "অধ্যায়",
            "url": "https://www.ebanglalibrary.com/books/sample/chapter/",
            "type": "lesson",
        },
        ["অধ্যায়"],
        ctx,
        book_manifest.normalize_manifest_limits(),
    )

    assert "অধ্যায়ের লেখা" in item["content"]
    assert ctx.cache == {}
    assert len(ctx.pages) == 1


def test_manifest_front_matter_stops_before_numeric_body_marker():
    sections_payload = book_manifest.normalize_body_sections(
        book_title="অপ্রাপণীয়া",
        landing_main_content="""
        <h2>ভূমিকা — অপ্রাপণীয়া</h2>
        <p>এটি বইয়ের দীর্ঘ ভূমিকার লেখা।</p>
        <p>০১.</p>
        <p>এই আখ্যানের মূল চরিত্র বহু বছর পরে দেশে ফিরছেন।</p>
        <p>০২.</p>
        <p>দ্বিতীয় অধ্যায়ের লেখা এখানে শুরু হচ্ছে।</p>
        """,
        toc_nodes=[],
        content_items=[],
    )

    assert [section["title"] for section in sections_payload["front_sections"]] == [
        "ভূমিকা — অপ্রাপণীয়া"
    ]
    assert [item["title"] for item in sections_payload["content_items"]] == ["১", "২"]
    assert sections_payload["main_content"] == ""


def test_manifest_disambiguates_duplicate_source_backed_paths():
    toc = [
        {
            "title": "সেইসব ঈদ",
            "path": ["সেইসব ঈদ"],
            "source_url": "https://www.ebanglalibrary.com/lessons/eid/",
            "has_content": True,
        },
        {
            "title": "সেইসব ঈদ",
            "path": ["সেইসব ঈদ"],
            "source_url": "https://www.ebanglalibrary.com/lessons/eid-2/",
            "has_content": True,
        },
    ]
    content_items = [
        {
            "title": "সেইসব ঈদ",
            "path": ["সেইসব ঈদ"],
            "source_url": "https://www.ebanglalibrary.com/lessons/eid/",
            "content": "<p>এক</p>",
        },
        {
            "title": "সেইসব ঈদ",
            "path": ["সেইসব ঈদ"],
            "source_url": "https://www.ebanglalibrary.com/lessons/eid-2/",
            "content": "<p>দুই</p>",
        },
    ]

    updated_toc, updated_items = book_manifest.disambiguate_duplicate_content_paths(
        toc,
        content_items,
    )

    assert [item["path"] for item in updated_items] == [
        ["সেইসব ঈদ"],
        ["সেইসব ঈদ (২)"],
    ]
    assert [entry["path"] for entry in updated_toc] == [
        ["সেইসব ঈদ"],
        ["সেইসব ঈদ (২)"],
    ]


def test_manifest_parser_expands_embedded_lesson_page_toc():
    """Container lessons should have sub-chapters discovered from the
    .ld-course-navigation sidebar's sub-chapter .ld-lesson-items container.

    LearnDash renders the sidebar with two types of .ld-lesson-items:
    - The course-level nav (includes .ld-is-current-lesson) — skipped.
    - The sub-chapter nav (no .ld-is-current-lesson) — used as children.

    Container lessons that also carry story content (like সহাবস্থান) are
    expanded correctly — story content must NOT prevent sub-chapter detection.
    Regular leaf lessons (only the course-level nav, no sub-chapter container)
    remain as leaf nodes.
    """
    source_url = "https://www.ebanglalibrary.com/books/container-book/"

    # Book page: two lessons with no inline topic entries (no data-ld-expand-id
    # and no .ld-table-list-item children).
    landing = BeautifulSoup(
        """
        <div class="ld-item-list ld-lesson-list">
          <div class="ld-item-list-items">
            <div class="ld-item-list-item ld-item-lesson-item">
              <a class="ld-item-name" href="https://www.ebanglalibrary.com/lessons/novel-a/">
                <div class="ld-item-title">উপন্যাস ক</div>
              </a>
            </div>
            <div class="ld-item-list-item ld-item-lesson-item">
              <a class="ld-item-name" href="https://www.ebanglalibrary.com/lessons/story-b/">
                <div class="ld-item-title">গল্প খ</div>
              </a>
            </div>
          </div>
        </div>
        """,
        "html.parser",
    )

    # Lesson page for "উপন্যাস ক": a container lesson that ALSO has story
    # content (like সহাবস্থান in the মুখোমুখি book).  The sidebar has two
    # .ld-lesson-items containers: the course-level nav (with
    # .ld-is-current-lesson) and the sub-chapter nav (without it).
    # Story content must NOT prevent expansion.
    novel_a_page = BeautifulSoup(
        """
        <article>
          <div class="entry-content"><p>উপন্যাস ক এর নিজস্ব গল্প।</p></div>
        </article>
        <div class="ld-course-navigation">
          <div class="ld-lesson-items" id="ld-lesson-list-100">
            <div class="ld-lesson-item ld-is-current-lesson">
              <div class="ld-lesson-item-preview">
                <a href="https://www.ebanglalibrary.com/lessons/novel-a/">উপন্যাস ক</a>
              </div>
            </div>
            <div class="ld-lesson-item ld-is-not-current-lesson">
              <div class="ld-lesson-item-preview">
                <a href="https://www.ebanglalibrary.com/lessons/story-b/">গল্প খ</a>
              </div>
            </div>
          </div>
          <div class="ld-lesson-items" id="ld-lesson-list-200">
            <div class="ld-lesson-item">
              <div class="ld-lesson-item-preview">
                <a href="https://www.ebanglalibrary.com/lessons/chapter-1/">অধ্যায় ১</a>
              </div>
            </div>
            <div class="ld-lesson-item">
              <div class="ld-lesson-item-preview">
                <a href="https://www.ebanglalibrary.com/lessons/chapter-2/">অধ্যায় ২</a>
              </div>
            </div>
            <div class="ld-lesson-item">
              <div class="ld-lesson-item-preview">
                <a href="https://www.ebanglalibrary.com/lessons/chapter-3/">অধ্যায় ৩</a>
              </div>
            </div>
          </div>
        </div>
        """,
        "html.parser",
    )

    # Lesson page for "গল্প খ": a regular leaf lesson.  The sidebar has only
    # the course-level .ld-lesson-items (with .ld-is-current-lesson), so no
    # sub-chapter container is present — it stays a leaf node.
    story_b_page = BeautifulSoup(
        """
        <article>
          <div class="entry-content"><p>এটি একটি ছোটগল্প।</p></div>
        </article>
        <div class="ld-course-navigation">
          <div class="ld-lesson-items" id="ld-lesson-list-100">
            <div class="ld-lesson-item ld-is-not-current-lesson">
              <div class="ld-lesson-item-preview">
                <a href="https://www.ebanglalibrary.com/lessons/novel-a/">উপন্যাস ক</a>
              </div>
            </div>
            <div class="ld-lesson-item ld-is-current-lesson">
              <div class="ld-lesson-item-preview">
                <a href="https://www.ebanglalibrary.com/lessons/story-b/">গল্প খ</a>
              </div>
            </div>
          </div>
        </div>
        """,
        "html.parser",
    )

    lesson_pages = {
        "https://www.ebanglalibrary.com/lessons/novel-a/": novel_a_page,
        "https://www.ebanglalibrary.com/lessons/story-b/": story_b_page,
    }

    class FakeContext:
        def __init__(self):
            self.fetched_urls = []

        def fetch_soup(self, url, **_kwargs):
            self.fetched_urls.append(url)
            return lesson_pages.get(url)

    ctx = FakeContext()
    toc_nodes, _meta = book_manifest.collect_learndash_toc(
        landing,
        source_url,
        ctx,
        book_manifest.normalize_manifest_limits(),
    )

    # Both lesson URLs are fetched to probe for embedded sub-chapter TOC.
    assert "https://www.ebanglalibrary.com/lessons/novel-a/" in ctx.fetched_urls
    assert "https://www.ebanglalibrary.com/lessons/story-b/" in ctx.fetched_urls

    # The container lesson is expanded even though it also has story content.
    novel_a = next(n for n in toc_nodes if n["title"] == "উপন্যাস ক")
    assert [child["title"] for child in novel_a["children"]] == [
        "অধ্যায় ১",
        "অধ্যায় ২",
        "অধ্যায় ৩",
    ]
    assert novel_a["children"][0]["type"] == "topic"
    assert novel_a["children"][0]["url"] == "https://www.ebanglalibrary.com/lessons/chapter-1/"

    # The regular leaf lesson (only course-level nav, no sub-chapter list) stays
    # a leaf node regardless of story content.
    story_b = next(n for n in toc_nodes if n["title"] == "গল্প খ")
    assert story_b["children"] == []
