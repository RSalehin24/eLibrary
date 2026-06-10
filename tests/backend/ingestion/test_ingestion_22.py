"""Phase D: classify_incoming_book duplicate-classification matrix.

Tests bypass the full scraped-book normaliser and inject a normalised
shape directly so each branch can be exercised in isolation.
"""
from __future__ import annotations

import pytest

from apps.catalog.models import (
    Book,
    BookContributor,
    Contributor,
    ContributorRole,
)
from apps.common.models import LifecycleState, ReviewState
from apps.ingestion.services.submissions_support.detection import (
    CLASSIFY_EXACT_DUPLICATE,
    CLASSIFY_NEEDS_REVIEW,
    CLASSIFY_NEW_EDITION,
    CLASSIFY_NEW_WORK,
    classify_incoming_book,
)


pytestmark = pytest.mark.django_db


def _make_book(*, title, authors=(), translators=(), publisher="", edition=""):
    book = Book.objects.create(
        title=title,
        source_site="example.com",
        state=LifecycleState.READY,
        review_state=ReviewState.APPROVED,
        manual_publisher=publisher,
        edition=edition,
    )
    for name in authors:
        contributor, _ = Contributor.objects.get_or_create(name=name)
        BookContributor.objects.create(book=book, contributor=contributor, role=ContributorRole.AUTHOR)
    for name in translators:
        contributor, _ = Contributor.objects.get_or_create(name=name)
        BookContributor.objects.create(book=book, contributor=contributor, role=ContributorRole.TRANSLATOR)
    return book


def _stub_normalizer(*, authors=(), translators=()):
    def _fn(scraped_data):
        contributors = []
        for name in authors:
            contributors.append({"name": name, "role": ContributorRole.AUTHOR, "raw_value": name})
        for name in translators:
            contributors.append({"name": name, "role": ContributorRole.TRANSLATOR, "raw_value": name})
        return {
            "title": scraped_data.get("book_title", ""),
            "contributors": contributors,
            "series": [],
            "categories": [],
            "raw_strings": {
                "manual_publisher": scraped_data.get("publisher", ""),
                "edition": scraped_data.get("edition", ""),
            },
        }
    return _fn


def _scraped(*, title, publisher="", edition=""):
    return {"book_title": title, "publisher": publisher, "edition": edition}


def test_classify_returns_new_work_when_no_title_match_exists():
    result = classify_incoming_book(
        _scraped(title="অপরিচিত বই"),
        normalize_scraped_book_fn=_stub_normalizer(authors=["লেখক ক"]),
    )
    assert result["verdict"] == CLASSIFY_NEW_WORK
    assert result["matched_book"] is None


def test_classify_returns_new_work_when_authors_differ():
    _make_book(title="শ্রেষ্ঠ কবিতা", authors=["কবি এক"])
    result = classify_incoming_book(
        _scraped(title="শ্রেষ্ঠ কবিতা"),
        normalize_scraped_book_fn=_stub_normalizer(authors=["কবি দুই"]),
    )
    assert result["verdict"] == CLASSIFY_NEW_WORK


def test_classify_returns_exact_duplicate_when_all_fields_overlap():
    _make_book(
        title="শ্রেষ্ঠ কবিতা",
        authors=["কবি এক"],
        translators=["অনুবাদক এক"],
        publisher="প্রকাশক এক",
        edition="২য়",
    )
    result = classify_incoming_book(
        _scraped(title="শ্রেষ্ঠ কবিতা", publisher="প্রকাশক এক", edition="২য়"),
        normalize_scraped_book_fn=_stub_normalizer(
            authors=["কবি এক"], translators=["অনুবাদক এক"]
        ),
    )
    assert result["verdict"] == CLASSIFY_EXACT_DUPLICATE
    assert result["matched_book"] is not None


def test_classify_returns_new_edition_when_publisher_differs():
    existing = _make_book(
        title="শ্রেষ্ঠ কবিতা",
        authors=["কবি এক"],
        publisher="প্রকাশক এক",
    )
    result = classify_incoming_book(
        _scraped(title="শ্রেষ্ঠ কবিতা", publisher="প্রকাশক দুই"),
        normalize_scraped_book_fn=_stub_normalizer(authors=["কবি এক"]),
    )
    assert result["verdict"] == CLASSIFY_NEW_EDITION
    assert result["matched_book"].id == existing.id


def test_classify_returns_new_edition_when_edition_differs():
    _make_book(title="শ্রেষ্ঠ কবিতা", authors=["কবি এক"], edition="১ম")
    result = classify_incoming_book(
        _scraped(title="শ্রেষ্ঠ কবিতা", edition="৩য়"),
        normalize_scraped_book_fn=_stub_normalizer(authors=["কবি এক"]),
    )
    assert result["verdict"] == CLASSIFY_NEW_EDITION


def test_classify_returns_new_edition_when_translator_differs():
    _make_book(
        title="শ্রেষ্ঠ কবিতা",
        authors=["কবি এক"],
        translators=["অনুবাদক এক"],
    )
    result = classify_incoming_book(
        _scraped(title="শ্রেষ্ঠ কবিতা"),
        normalize_scraped_book_fn=_stub_normalizer(
            authors=["কবি এক"], translators=["অনুবাদক দুই"]
        ),
    )
    assert result["verdict"] == CLASSIFY_NEW_EDITION


def test_classify_needs_review_when_existing_book_has_no_authors():
    existing = _make_book(title="শ্রেষ্ঠ কবিতা")  # no authors
    result = classify_incoming_book(
        _scraped(title="শ্রেষ্ঠ কবিতা"),
        normalize_scraped_book_fn=_stub_normalizer(authors=["কবি এক"]),
    )
    assert result["verdict"] == CLASSIFY_NEEDS_REVIEW
    assert result["matched_book"].id == existing.id


def test_classify_needs_review_when_incoming_has_no_authors():
    existing = _make_book(title="শ্রেষ্ঠ কবিতা", authors=["কবি এক"])
    result = classify_incoming_book(
        _scraped(title="শ্রেষ্ঠ কবিতা"),
        normalize_scraped_book_fn=_stub_normalizer(),
    )
    assert result["verdict"] == CLASSIFY_NEEDS_REVIEW
    assert result["matched_book"].id == existing.id
