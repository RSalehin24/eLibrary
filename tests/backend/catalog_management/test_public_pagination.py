import pytest
from apps.catalog.models import Book

pytestmark = pytest.mark.django_db


def test_public_numbered_pages_match_cursor_feed(client):
    for index in range(3):
        Book.objects.create(title=f"প্রকাশিত {index}", state="published")
    first = client.get("/api/v1/catalog/books/", {"page": 1, "limit": 2}).json()
    second = client.get("/api/v1/catalog/books/", {"page": 2, "limit": 2}).json()
    cursor_page = client.get(
        "/api/v1/catalog/books/", {"cursor": first["next_cursor"], "limit": 2}
    ).json()
    assert len(first["entries"]) == 2
    assert len(second["entries"]) == 1
    assert {key: value for key, value in second.items() if key != "pagination"} == {
        key: value for key, value in cursor_page.items() if key != "pagination"
    }
    assert first["pagination"] == {
        "page": 1,
        "limit": 2,
        "total_count": 3,
        "page_count": 2,
    }
    assert second["pagination"]["page"] == 2
    assert cursor_page["pagination"] == {
        "page": None,
        "limit": 2,
        "total_count": 3,
        "page_count": 2,
    }
    response = client.get(
        "/api/v1/catalog/books/", {"page": 2, "cursor": first["next_cursor"]}
    )
    assert response.status_code == 400
    assert "cursor" in response.json()["field_errors"]
