import pytest
from apps.access.models import Highlight

pytestmark = pytest.mark.django_db


def test_personal_notes_restore_separate_views_search_color_and_safe_recolor(
    reader, annotation_session
):
    client, user, book, _, publication = reader
    base = {
        "user": user,
        "book": book,
        "prepared_publication": publication,
        "cfi_range": "legacy",
        "text": "Find this passage",
    }
    plain = Highlight.objects.create(**base, kind="highlight", note="", color="yellow")
    note = Highlight.objects.create(
        **base, kind="highlight", note="Personal thought", color="green"
    )
    quote = Highlight.objects.create(
        **base, kind="quote", note="Quoted passage", color="pink"
    )
    path = "/api/v1/me/highlights/"
    assert client.get(path, {"include_counts": True}).json()["counts"] == {
        "highlights": 1,
        "notes": 1,
        "quotes": 1,
        "bookmarks": 0,
    }
    for view, expected in [("highlights", plain), ("notes", note), ("quotes", quote)]:
        data = client.get(path, {"view": view}).json()
        assert [entry["id"] for entry in data["entries"]] == [str(expected.pk)]
    assert client.get(path, {"view": "notes", "q": "thought", "color": "green"}).json()[
        "entries"
    ][0]["id"] == str(note.pk)
    assert not client.get(path, {"view": "notes", "color": "yellow"}).json()["entries"]
    assert client.get(path, {"view": "invalid"}).status_code == 400
    assert client.get(path, {"color": "invalid"}).status_code == 400
    detail = path + str(note.pk) + "/"
    values = {
        "note": note.note,
        "color": "blue",
        "kind": "quote",
        "expected_updated_at": note.updated_at.isoformat(),
    }
    changed = client.patch(detail, values, format="json")
    assert changed.status_code == 200 and changed.json()["color"] == "blue"
    assert changed.json()["kind"] == "quote"
    assert client.patch(detail, values, format="json").status_code == 409
    note.refresh_from_db()
    assert note.text == base["text"] and note.cfi_range == "legacy"
    assert (
        client.patch(
            detail,
            {
                **values,
                "color": "bad",
                "expected_updated_at": note.updated_at.isoformat(),
            },
            format="json",
        ).status_code
        == 400
    )
