import json

import pytest
from apps.access.models import Bookmark

pytestmark = pytest.mark.django_db


def values(**overrides):
    anchor = {"chapter": 0, "offset": 12, "quote": "বাংলা 🪷 একটি জায়গা"}
    return {
        "location": "text:" + json.dumps({**anchor, **overrides}, ensure_ascii=False),
        "chapter_href": "OEBPS/chapter-1.xhtml",
        "chapter_label": "প্রথম অধ্যায়",
        "preview_text": anchor["quote"],
        "note": "নিজের নোট",
    }


def test_text_bookmarks_preserve_exact_offsets_quotes_and_notes_idempotently(
    reader, annotation_session
):
    path = f"{annotation_session}/bookmarks/"
    original = reader[0].put(path, values(), format="json")
    assert original.status_code == 200
    anchor = json.loads(original.json()["location"].removeprefix("text:"))
    assert anchor == {"chapter": 0, "offset": 12, "quote": "বাংলা 🪷 একটি জায়গা"}
    repeated = reader[0].put(path, {**values(), "note": "অন্য নোট"}, format="json")
    assert repeated.status_code == 200
    assert repeated.json()["id"] == original.json()["id"]
    assert repeated.json()["note"] == "নিজের নোট"
    assert Bookmark.objects.count() == 1


@pytest.mark.parametrize(
    "override",
    [
        {"chapter": -1},
        {"chapter": 1},
        {"chapter": 10000},
        {"chapter": True},
        {"offset": -1},
        {"offset": 32_000_001},
        {"offset": 1.5},
        {"offset": True},
        {"quote": ""},
        {"quote": " "},
        {"quote": "ক" * 33},
        {"extra": "unsupported"},
    ],
)
def test_text_bookmarks_reject_malformed_or_wrong_chapter_positions(
    reader, annotation_session, override
):
    response = reader[0].put(
        f"{annotation_session}/bookmarks/", values(**override), format="json"
    )
    assert response.status_code == 400
    assert not Bookmark.objects.exists()


@pytest.mark.parametrize(
    "location", ["text:[]", "text:null", 'text:{"chapter":0}', "text:not-json"]
)
def test_text_bookmarks_reject_invalid_anchor_payloads(
    reader, annotation_session, location
):
    response = reader[0].put(
        f"{annotation_session}/bookmarks/",
        {**values(), "location": location},
        format="json",
    )
    assert response.status_code == 400


def test_text_anchor_for_another_chapter_is_rejected_even_when_that_chapter_exists(
    reader, annotation_session
):
    response = reader[0].put(
        f"{annotation_session}/bookmarks/", values(chapter=1), format="json"
    )
    assert response.status_code == 400 and "location" in response.json()["field_errors"]
