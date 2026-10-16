from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, MetadataVersion
from django.db import close_old_connections, connections
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db(transaction=True)


def save_at_revision(user, book, barrier):
    close_old_connections()
    try:
        client = APIClient()
        client.force_authenticate(user)
        barrier.wait(timeout=10)
        response = client.patch(
            f"/api/v1/manage/books/{book.slug}/",
            {
                "expected_updated_at": book.updated_at.isoformat(),
                "summary": "সমান্তরাল সম্পাদনা",
            },
            format="json",
        )
        return response.status_code
    finally:
        connections.close_all()


def test_only_one_concurrent_editor_can_save_the_same_revision():
    user = User.objects.create_user(
        email="concurrent-editor@library.test", is_staff=True
    )
    book = Book.objects.create(title="একই সংস্করণের সম্পাদনা")
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: save_at_revision(user, book, barrier), range(2))
        )
    assert sorted(results) == [200, 409]
    assert MetadataVersion.objects.filter(book=book).count() == 1
    book.refresh_from_db()
    assert book.summary == "সমান্তরাল সম্পাদনা"
