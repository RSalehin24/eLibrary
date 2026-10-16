import pytest
from apps.catalog.models import Book

pytestmark = pytest.mark.django_db


def test_public_numbered_pages_match_cursor_feed(client):
    for index in range(3):
        Book.objects.create(
            title=f"প্রকাশিত {index}", state="published", review_state="approved"
        )
    first = client.get("/api/v1/catalog/books/", {"page": 1, "limit": 2}).json()
    second = client.get("/api/v1/catalog/books/", {"page": 2, "limit": 2}).json()
    cursor_page = client.get(
        "/api/v1/catalog/books/", {"cursor": first["next_cursor"], "limit": 2}
    ).json()
    assert len(first["entries"]) == 2
    assert len(second["entries"]) == 1
    assert second == cursor_page
    response = client.get(
        "/api/v1/catalog/books/", {"page": 2, "cursor": first["next_cursor"]}
    )
    assert response.status_code == 400
    assert "cursor" in response.json()["field_errors"]
