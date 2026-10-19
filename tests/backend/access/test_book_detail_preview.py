import pytest
from apps.access.models import BookOpeningRecord, PermissionGrant, PermissionScope
from apps.access.reading.detail_preview import (
    MAX_CONTENTS_ENTRIES,
    MAX_TEXT_CHARACTERS,
    contents_preview,
)
from apps.accounts.models import User
from apps.catalog.models import UserBook
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def details_path(book):
    return f"/api/v1/reading/books/{book.slug}/details/"


def test_owner_gets_plain_metadata_dedication_and_nested_contents(reader):
    client, _, book, _, _ = reader
    book.book_info_html = "<p>প্রকাশকাল: ২০২০</p>"
    book.dedication_html = "<p>প্রিয় পাঠককে</p><script>private-script</script>"
    book.toc = [{
        "title": "প্রথম খণ্ড", "source_url": "https://private.invalid/chapter/",
        "content": "private-chapter-body", "children": [{"title": "প্রথম অধ্যায়"}],
    }]
    book.save()
    response = client.get(details_path(book))
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    data = response.json()
    assert data["dedication"] == "প্রিয় পাঠককে"
    assert data["contents"] == [
        {"label": "প্রথম খণ্ড", "depth": 0},
        {"label": "প্রথম অধ্যায়", "depth": 1},
    ]
    assert data["front_matter"] == [{"label": "প্রথম প্রকাশ", "value": "২০২০"}]
    assert data["truncated"] is False
    for private_value in ["private-script", "private-chapter-body", "private.invalid"]:
        assert private_value not in response.content.decode()


def test_preview_requires_current_read_access_and_never_consumes_an_opening(reader):
    client, user, book, _, _ = reader
    assert APIClient().get(details_path(book)).status_code == 403
    UserBook.objects.filter(user=user, book=book).delete()
    assert client.get(details_path(book)).status_code == 403
    grant = PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_ONCE
    )
    assert client.get(details_path(book)).status_code == 200
    assert not BookOpeningRecord.objects.filter(user=user, book=book).exists()
    assert client.post(f"/api/v1/reading/books/{book.slug}/launch/").status_code == 200
    assert client.get(details_path(book)).status_code == 403
    grant.scope = PermissionScope.READ_DURABLE
    grant.save()
    assert client.get(details_path(book)).status_code == 200
    grant.is_active = False
    grant.save()
    assert client.get(details_path(book)).status_code == 403


def test_other_account_cannot_see_protected_preview(reader):
    client, _, book, _, _ = reader
    client.force_authenticate(User.objects.create_user(email="preview-other@test.invalid"))
    assert client.get(details_path(book)).status_code == 403


@pytest.mark.parametrize("unavailable", ["deleted", "manual", "quarantined"])
def test_unavailable_book_preview_is_denied_even_to_owner(reader, unavailable):
    client, _, book, _, _ = reader
    if unavailable == "deleted":
        book.deleted_at = timezone.now()
    elif unavailable == "manual":
        book.record_type = "manual"
    else:
        book.source_quality_state = "quarantined"
    book.save()
    assert client.get(details_path(book)).status_code == (403 if unavailable == "quarantined" else 404)


def test_preview_bounds_text_and_contents_and_reports_shortening(reader):
    client, _, book, _, _ = reader
    book.dedication_html = "x" * (MAX_TEXT_CHARACTERS + 1)
    book.toc = [{"title": f"অধ্যায় {number}"} for number in range(MAX_CONTENTS_ENTRIES + 1)]
    book.save()
    data = client.get(details_path(book)).json()
    assert len(data["dedication"]) == MAX_TEXT_CHARACTERS
    assert len(data["contents"]) == MAX_CONTENTS_ENTRIES
    assert data["truncated"] is True


def test_nested_and_malformed_contents_are_bounded_without_raw_locators():
    nodes = [{"title": "শেষ"}]
    for _depth in range(12):
        nodes = [{"title": "খণ্ড", "children": nodes}]
    entries, truncated = contents_preview(nodes)
    assert len(entries) == 9
    assert max(entry["depth"] for entry in entries) == 8
    assert truncated is True
    assert contents_preview([None, False, "invalid", {"title": "<script>secret</script>"}]) == ([], False)
    assert contents_preview([None, {"label": "অধ্যায়"}]) == ([{"label": "অধ্যায়", "depth": 0}], False)


def test_anonymous_catalog_metadata_does_not_include_source_preview(reader):
    _, _, book, _, _ = reader
    book.state = "published"
    book.dedication_html = "protected-dedication"
    book.save()
    response = APIClient().get(f"/api/v1/catalog/books/{book.slug}/")
    assert response.status_code == 200
    assert "protected-dedication" not in response.content.decode()
    assert "dedication" not in response.json()
