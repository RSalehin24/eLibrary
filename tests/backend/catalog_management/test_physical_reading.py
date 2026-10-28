import pytest
from apps.accounts.models import User
from apps.catalog.models import Book
from django.apps import apps
from django.db import connection
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("administrator", [False, True])
@pytest.mark.parametrize("method", ["get", "put", "post", "delete"])
def test_physical_reading_routes_are_absent_for_every_actor(administrator, method):
    user = User.objects.create_user(email="reader@library.test", is_staff=administrator)
    client = APIClient()
    client.force_authenticate(user)
    book = Book.objects.create(title="একটি বই")
    response = getattr(client, method)(f"/api/v1/me/books/{book.slug}/physical-log/")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/catalog/physical-books/",
        "/api/v1/catalog/physical-books/export/",
        "/api/catalog/manual-books/",
    ],
)
def test_physical_catalog_and_exports_have_no_route(path):
    client = APIClient()
    client.force_authenticate(
        User.objects.create_user(email="admin@library.test", is_staff=True)
    )
    assert client.get(path).status_code == 404
    assert client.post(path, {"title": "obsolete"}, format="json").status_code == 404
    assert not Book.objects.exists()


def test_fresh_schema_contains_no_physical_or_review_storage():
    with pytest.raises(LookupError):
        apps.get_model("catalog", "PhysicalReadingLog")
    with pytest.raises(LookupError):
        apps.get_model("catalog", "MetadataReview")
    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, "catalog_book"
            )
        }
        tables = connection.introspection.table_names(cursor)
    assert (
        not {
            "record_type",
            "manual_binding",
            "manual_price",
            "manual_publisher",
            "manual_language",
            "manual_is_compilation",
            "review_state",
            "metadata_last_reviewed_at",
            "editorial_reviewed_at",
        }
        & columns
    )
    assert {"publisher", "language", "is_compilation"} <= columns
    assert "catalog_physicalreadinglog" not in tables
    assert "catalog_metadatareview" not in tables
