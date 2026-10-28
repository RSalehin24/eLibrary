import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookSource,
)


def assert_access_model_constraints(client):
    from django.db.utils import IntegrityError

    # 1. Test uniqueness of BookSource
    book = Book.objects.create(title="Source Book", state="ready")
    BookSource.objects.create(
        book=book,
        source_url="https://example.com/1",
        normalized_source_url="https://example.com/1",
    )
    from django.db import transaction

    with pytest.raises(IntegrityError), transaction.atomic():
        BookSource.objects.create(
            book=book,
            source_url="https://example.com/2",
            normalized_source_url="https://example.com/2",
        )

    # 2. Setup user and test visibility
    user = User.objects.create_user(
        email="reader@example.com", password="strong-password-123"
    )
    client.force_login(user)

    # Without permission, source_urls and source_records should be empty
    response = client.get(f"/api/catalog/books/{book.slug}/")
    assert response.status_code == 200
    data = response.json()
    assert data["source_urls"] == []
    assert data["source_records"] == []

    # Grant VIEW_SOURCE_RECORDS permission
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.VIEW_SOURCE_RECORDS
    )

    # With permission, they should be visible
    response = client.get(f"/api/catalog/books/{book.slug}/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["source_urls"]) == 1
    assert data["source_urls"][0] == "https://example.com/1"
    assert len(data["source_records"]) == 1
    assert data["source_records"][0]["url"] == "https://example.com/1"

    # Super admin should see it automatically
    superadmin = User.objects.create_superuser(
        email="super@example.com", password="strong-password-123"
    )
    client.force_login(superadmin)
    response = client.get(f"/api/catalog/books/{book.slug}/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["source_urls"]) == 1
