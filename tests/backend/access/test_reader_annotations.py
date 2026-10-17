from datetime import timedelta
from urllib.parse import urlencode

import pytest
from apps.access.models import Bookmark, Highlight, PreviewAccessSession
from apps.access.publication_models import PreparationState, PreparedPublication
from apps.accounts.models import User
from apps.catalog.models import Book, UserBook
from django.db import IntegrityError, transaction
from django.test import Client
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.fixture
def annotation_session(reader):
    client, _, book, _, _ = reader
    session = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    return f"/api/v1/reading/sessions/{session['id']}"


def bookmark_values(**overrides):
    return {
        "location": "chapter:0:0.5",
        "chapter_href": "OEBPS/chapter-1.xhtml",
        "chapter_label": "প্রথম অধ্যায়",
        "note": "নিজের কথা",
        **overrides,
    }


def highlight_values(**overrides):
    return {
        "chapter_href": "OEBPS/chapter-1.xhtml",
        "selector": {"start": 0, "end": 4},
        "text": "বাংলা",
        "note": "মনে রাখি",
        **overrides,
    }


def test_bookmark_save_is_idempotent_and_normalizes_positions(
    reader, annotation_session
):
    client = reader[0]
    path = f"{annotation_session}/bookmarks/"
    first = client.put(path, bookmark_values(), format="json")
    second = client.put(
        path,
        bookmark_values(location="chapter:00:0.50000", note="stale"),
        format="json",
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["note"] == "নিজের কথা"
    assert second.json()["location"] == "chapter:0:0.5000"
    assert Bookmark.objects.count() == 1
    assert "prepared_publication" not in first.json() and "user" not in first.json()


@pytest.mark.parametrize(
    "values",
    [
        {"location": "chapter:0:1.1"},
        {"location": "chapter:2:0"},
        {"location": "chapter:1:0"},
        {"chapter_href": "../secret.xhtml"},
        {"note": "x" * 5001},
    ],
)
def test_bookmarks_reject_invalid_positions_and_inputs(
    reader, annotation_session, values
):
    response = reader[0].put(
        f"{annotation_session}/bookmarks/", bookmark_values(**values), format="json"
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid"
    assert not Bookmark.objects.exists()


def test_highlights_preserve_plain_text_and_validated_selectors(
    reader, annotation_session
):
    client = reader[0]
    response = client.post(
        f"{annotation_session}/highlights/",
        highlight_values(tags=["চিন্তা"], color="green"),
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["selector"] == {"start": 0, "end": 4}
    assert response.json()["tags"] == ["চিন্তা"]
    assert response.json()["color"] == "green"
    assert (
        client.get(f"{annotation_session}/highlights/").json()["entries"][0]["text"]
        == "বাংলা"
    )


@pytest.mark.parametrize(
    "values",
    [
        {"selector": {"start": 2, "end": 1}},
        {"selector": {"start": -1, "end": 2}},
        {"chapter_href": "other.xhtml"},
        {"text": ""},
        {"color": "red"},
        {"tags": ["tag"] * 11},
        {"text": "x" * 5001},
    ],
)
def test_highlights_validate_input(reader, annotation_session, values):
    response = reader[0].post(
        f"{annotation_session}/highlights/", highlight_values(**values), format="json"
    )
    assert response.status_code == 400
    assert not Highlight.objects.exists()


def test_annotations_are_separate_between_editions(reader, annotation_session):
    client, user, book, _, publication = reader
    original = client.put(
        f"{annotation_session}/bookmarks/", bookmark_values(), format="json"
    ).json()
    newer = PreparedPublication.objects.create(
        checksum="f" * 64,
        state=PreparationState.READY,
        manifest=publication.manifest,
        storage_reference="e" * 64,
    )
    session = PreviewAccessSession.objects.create(
        user=user, book=book, prepared_publication=newer
    )
    path = f"/api/v1/reading/sessions/{session.pk}/bookmarks/"
    assert client.get(path).json()["entries"] == []
    fresh = client.put(path, bookmark_values(), format="json").json()
    assert original["id"] != fresh["id"]
    assert Bookmark.objects.count() == 2


def test_legacy_bookmarks_keep_uniqueness_and_remain_visible(
    reader, annotation_session
):
    client, user, book, _, _ = reader
    legacy = Bookmark.objects.create(user=user, book=book, location="epubcfi(/6/2)")
    with pytest.raises(IntegrityError), transaction.atomic():
        Bookmark.objects.create(user=user, book=book, location=legacy.location)
    entries = client.get(f"{annotation_session}/bookmarks/").json()["entries"]
    assert entries[0]["location"] == legacy.location


@pytest.mark.parametrize(
    "kind,values",
    [("bookmarks", bookmark_values()), ("highlights", highlight_values())],
)
def test_annotation_edits_detect_conflicts_and_owner_boundaries(
    reader, annotation_session, kind, values
):
    client = reader[0]
    method = client.put if kind == "bookmarks" else client.post
    created = method(f"{annotation_session}/{kind}/", values, format="json").json()
    path = f"{annotation_session}/{kind}/{created['id']}/"
    update = {"expected_updated_at": created["updated_at"], "note": "পরের কথা"}
    assert client.patch(path, update, format="json").status_code == 200
    assert client.patch(path, update, format="json").status_code == 409
    client.force_authenticate(
        User.objects.create_user(email="annotation-stranger@library.test")
    )
    assert client.patch(path, update, format="json").status_code == 404
    assert client.delete(path).status_code == 404


def test_personal_notes_survive_revocation_and_expiry(reader, annotation_session):
    client, user, book, _, _ = reader
    created = client.post(
        f"{annotation_session}/highlights/", highlight_values(), format="json"
    ).json()
    UserBook.objects.filter(user=user, book=book).delete()
    PreviewAccessSession.objects.filter(user=user).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert client.get(f"{annotation_session}/highlights/").status_code == 404
    path = f"/api/v1/me/highlights/{created['id']}/"
    assert client.get(path).json()["text"] == "বাংলা"
    assert (
        client.patch(
            path,
            {"expected_updated_at": created["updated_at"], "note": "নিজের নতুন কথা"},
            format="json",
        ).status_code
        == 200
    )
    client.force_authenticate(
        User.objects.create_user(email="notes-stranger@library.test")
    )
    assert client.get(path).status_code == 404
    assert client.delete(path).status_code == 404
    client.force_authenticate(user)
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == 404


def test_personal_annotation_lists_are_bounded_and_lightweight(
    reader, annotation_session, django_assert_num_queries
):
    client, user, book, _, publication = reader
    Highlight.objects.bulk_create(
        [
            Highlight(
                user=user,
                book=book,
                prepared_publication=publication,
                cfi_range="legacy",
                text="x" * 5000,
                note="n" * 5000,
            )
            for _ in range(25)
        ]
    )
    with django_assert_num_queries(1):
        response = client.get("/api/v1/me/highlights/")
    data = response.json()
    assert len(data["entries"]) == 24 and data["has_more"]
    assert len(data["entries"][0]["text_preview"]) == 280
    assert len(data["entries"][0]["note_preview"]) == 280
    assert "text" not in data["entries"][0] and "note" not in data["entries"][0]
    parameters = urlencode({"cursor": data["next_cursor"]})
    following = client.get(f"/api/v1/me/highlights/?{parameters}").json()
    assert len(following["entries"]) == 1 and not following["has_more"]
    assert client.get(f"/api/v1/me/bookmarks/?{parameters}").status_code == 400
    assert (
        client.get(f"/api/v1/me/highlights/?q=changed&{parameters}").status_code == 400
    )
    client.force_authenticate(
        User.objects.create_user(email="cursor-stranger@library.test")
    )
    assert client.get(f"/api/v1/me/highlights/?{parameters}").status_code == 400


@pytest.mark.parametrize(
    "kind,model", [("bookmarks", Bookmark), ("highlights", Highlight)]
)
def test_personal_notes_filter_by_book_and_bind_cursors_to_that_book(
    reader, kind, model
):
    client, user, book, _, _ = reader
    other = Book.objects.create(title="Other notes book", slug="other-notes-book")
    stranger = User.objects.create_user(email="book-notes-stranger@library.test")
    model.objects.bulk_create(
        [
            model(
                user=user,
                book=book,
                **(
                    {"location": f"legacy-{index}"}
                    if kind == "bookmarks"
                    else {"cfi_range": f"legacy-{index}"}
                ),
            )
            for index in range(2)
        ]
    )
    model.objects.create(user=user, book=other)
    model.objects.create(user=stranger, book=book)
    path = f"/api/v1/me/{kind}/"
    first = client.get(path, {"book": book.slug, "limit": 1}).json()
    assert len(first["entries"]) == 1 and first["has_more"]
    assert first["entries"][0]["book_slug"] == book.slug
    cursor = first["next_cursor"]
    following = client.get(
        path, {"book": book.slug, "limit": 1, "cursor": cursor}
    ).json()
    assert len(following["entries"]) == 1 and not following["has_more"]
    assert client.get(path, {"book": other.slug, "cursor": cursor}).status_code == 400
    assert client.get(path, {"cursor": cursor}).status_code == 400
    assert client.get(path, {"book": "unknown"}).json()["entries"] == []
    assert client.get(path, {"book": "x" * 256}).status_code == 400


def test_annotation_mutations_require_csrf(reader, annotation_session):
    client = Client(enforce_csrf_checks=True)
    client.force_login(reader[1])
    path = f"{annotation_session}/bookmarks/"
    assert (
        client.put(path, bookmark_values(), content_type="application/json").status_code
        == 403
    )
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    assert (
        client.put(
            path,
            bookmark_values(),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 200
    )
