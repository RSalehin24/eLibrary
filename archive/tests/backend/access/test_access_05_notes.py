"""Tests for the Highlight/Quote/Bookmark notes flows.

Exercises:
- ``Highlight.kind`` field defaults and ``quote`` variant
- ``MyNotesView`` (``/api/access/me/notes/``) returns three buckets and respects
  ``kind``/``color``/``q``/``book`` query params
- Reader token highlight endpoint accepts ``kind="quote"`` payloads
- Slug-based highlight endpoint requires reader access
"""
from pathlib import Path

import pytest
from django.urls import reverse

from apps.access.models import (
    Bookmark,
    Highlight,
    HighlightKind,
    PermissionGrant,
    PermissionScope,
)
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
)
from apps.common.epub_utils import build_simple_epub


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(email="notes-user@example.com"):
    return User.objects.create_user(email=email, password="strong-password-123")


def _make_book(title="Notes Book", slug=None):
    book = Book.objects.create(
        title=title,
        state="ready",
        review_state="approved",
    )
    if slug:
        book.slug = slug
        book.save(update_fields=["slug"])
    return book


def _grant_read(user, book):
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_DURABLE
    )


def _attach_epub(book, tmp_path, filename="notes-reader.epub"):
    epub_path = Path(tmp_path) / filename
    epub_path.write_bytes(build_simple_epub(book.title))
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_highlight_default_kind_is_highlight():
    user = _make_user()
    book = _make_book()
    obj = Highlight.objects.create(
        user=user,
        book=book,
        cfi_range="epubcfi(/6/4!/4/2)",
        text="Sample",
        color="yellow",
    )
    assert obj.kind == HighlightKind.HIGHLIGHT == "highlight"


@pytest.mark.django_db
def test_highlight_kind_quote_persists():
    user = _make_user()
    book = _make_book()
    obj = Highlight.objects.create(
        user=user,
        book=book,
        cfi_range="epubcfi(/6/4!/4/2)",
        text="Quotable line",
        color="yellow",
        kind=HighlightKind.QUOTE,
    )
    obj.refresh_from_db()
    assert obj.kind == "quote"


# ---------------------------------------------------------------------------
# MyNotesView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_my_notes_returns_three_buckets(client):
    user = _make_user()
    book = _make_book()
    Bookmark.objects.create(user=user, book=book, location="ch-1", label="B")
    Highlight.objects.create(
        user=user,
        book=book,
        cfi_range="epubcfi(/6/4!/4/2)",
        text="Highlighted",
        color="yellow",
    )
    Highlight.objects.create(
        user=user,
        book=book,
        cfi_range="epubcfi(/6/4!/4/4)",
        text="Quoted",
        color="yellow",
        kind=HighlightKind.QUOTE,
    )

    client.force_login(user)
    response = client.get("/api/access/me/notes/")
    assert response.status_code == 200
    data = response.json()
    assert {"bookmarks", "highlights", "quotes"} <= set(data.keys())
    assert len(data["bookmarks"]) == 1
    assert len(data["highlights"]) == 1
    assert data["highlights"][0]["kind"] == "highlight"
    assert len(data["quotes"]) == 1
    assert data["quotes"][0]["kind"] == "quote"


@pytest.mark.django_db
def test_my_notes_kind_param_filters_to_single_bucket(client):
    user = _make_user()
    book = _make_book()
    Highlight.objects.create(
        user=user,
        book=book,
        cfi_range="x",
        text="A",
        color="yellow",
    )
    Highlight.objects.create(
        user=user,
        book=book,
        cfi_range="y",
        text="B",
        color="yellow",
        kind=HighlightKind.QUOTE,
    )

    client.force_login(user)

    only_quotes = client.get("/api/access/me/notes/?kind=quotes").json()
    assert "quotes" in only_quotes
    assert "highlights" not in only_quotes
    assert "bookmarks" not in only_quotes
    assert all(item["kind"] == "quote" for item in only_quotes["quotes"])

    only_highlights = client.get("/api/access/me/notes/?kind=highlights").json()
    assert "highlights" in only_highlights
    assert "quotes" not in only_highlights
    assert all(item["kind"] == "highlight" for item in only_highlights["highlights"])


@pytest.mark.django_db
def test_my_notes_color_filter_applies_only_to_highlights(client):
    user = _make_user()
    book = _make_book()
    Highlight.objects.create(
        user=user, book=book, cfi_range="a", text="y", color="yellow"
    )
    Highlight.objects.create(
        user=user, book=book, cfi_range="b", text="g", color="green"
    )

    client.force_login(user)
    data = client.get("/api/access/me/notes/?kind=highlights&color=yellow").json()
    assert len(data["highlights"]) == 1
    assert data["highlights"][0]["color"] == "yellow"


@pytest.mark.django_db
def test_my_notes_query_substring_search(client):
    user = _make_user()
    book = _make_book()
    Highlight.objects.create(
        user=user, book=book, cfi_range="a", text="hello world", color="yellow"
    )
    Highlight.objects.create(
        user=user, book=book, cfi_range="b", text="goodbye world", color="yellow"
    )

    client.force_login(user)
    data = client.get("/api/access/me/notes/?kind=highlights&q=hello").json()
    assert len(data["highlights"]) == 1
    assert "hello" in data["highlights"][0]["text"]


@pytest.mark.django_db
def test_my_notes_book_slug_filter(client):
    user = _make_user()
    book_a = _make_book(title="Book A")
    book_b = _make_book(title="Book B")
    Highlight.objects.create(
        user=user, book=book_a, cfi_range="a", text="A text", color="yellow"
    )
    Highlight.objects.create(
        user=user, book=book_b, cfi_range="b", text="B text", color="yellow"
    )

    client.force_login(user)
    data = client.get(
        f"/api/access/me/notes/?kind=highlights&book={book_a.slug}"
    ).json()
    assert len(data["highlights"]) == 1
    assert data["highlights"][0]["text"] == "A text"


@pytest.mark.django_db
def test_my_notes_requires_authentication(client):
    response = client.get("/api/access/me/notes/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_my_notes_does_not_leak_across_users(client):
    user_a = _make_user("a@example.com")
    user_b = _make_user("b@example.com")
    book = _make_book()
    Highlight.objects.create(
        user=user_a, book=book, cfi_range="a", text="A note", color="yellow"
    )
    Highlight.objects.create(
        user=user_b, book=book, cfi_range="b", text="B note", color="yellow"
    )

    client.force_login(user_a)
    data = client.get("/api/access/me/notes/?kind=highlights").json()
    assert len(data["highlights"]) == 1
    assert data["highlights"][0]["text"] == "A note"


# ---------------------------------------------------------------------------
# Reader token highlight endpoint (in-reader create) — must accept kind=quote
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reader_token_highlight_accepts_quote_kind(tmp_path, client):
    user = _make_user("quoter@example.com")
    book = _make_book(title="Quoter Book")
    _attach_epub(book, tmp_path, "quoter.epub")
    _grant_read(user, book)
    client.force_login(user)

    launch = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert launch.status_code == 200
    manifest = client.get(
        launch.json()["manifest_url"].replace("http://testserver", "")
    ).json()
    highlights_url = manifest["highlights_url"].replace("http://testserver", "")

    created = client.post(
        highlights_url,
        data={
            "cfi_range": "epubcfi(/6/4!/4/2)",
            "text": "Memorable quote",
            "color": "yellow",
            "kind": "quote",
        },
        content_type="application/json",
    )
    assert created.status_code == 201, created.content
    assert created.json()["kind"] == "quote"

    # Saved quote shows up in /me/notes/ under quotes (not highlights).
    notes = client.get("/api/access/me/notes/").json()
    assert any(q["text"] == "Memorable quote" for q in notes["quotes"])
    assert all(h["text"] != "Memorable quote" for h in notes["highlights"])


@pytest.mark.django_db
def test_reader_token_highlight_defaults_to_highlight_kind(tmp_path, client):
    user = _make_user("default-kind@example.com")
    book = _make_book(title="Default Kind Book")
    _attach_epub(book, tmp_path, "default-kind.epub")
    _grant_read(user, book)
    client.force_login(user)

    launch = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    manifest = client.get(
        launch.json()["manifest_url"].replace("http://testserver", "")
    ).json()
    highlights_url = manifest["highlights_url"].replace("http://testserver", "")

    created = client.post(
        highlights_url,
        data={
            "cfi_range": "epubcfi(/6/4!/4/2)",
            "text": "Normal highlight",
            "color": "yellow",
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    assert created.json()["kind"] == "highlight"


# ---------------------------------------------------------------------------
# Slug-based highlight endpoint guardrails
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_slug_highlight_create_requires_reader_access(client):
    user = _make_user("no-access@example.com")
    book = _make_book(title="Locked Book")
    client.force_login(user)

    blocked = client.post(
        f"/api/access/books/{book.slug}/highlights/",
        data={"cfi_range": "x", "text": "t", "color": "yellow"},
        content_type="application/json",
    )
    assert blocked.status_code == 403

    _grant_read(user, book)
    allowed = client.post(
        f"/api/access/books/{book.slug}/highlights/",
        data={"cfi_range": "x", "text": "t", "color": "yellow", "kind": "quote"},
        content_type="application/json",
    )
    assert allowed.status_code == 201
    assert allowed.json()["kind"] == "quote"
