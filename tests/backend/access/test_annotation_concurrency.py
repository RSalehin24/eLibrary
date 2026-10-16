from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from apps.access.models import Bookmark
from django.db import close_old_connections, connections
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db(transaction=True)


def edit_at_revision(user, annotation, barrier):
    close_old_connections()
    try:
        client = APIClient()
        client.force_authenticate(user)
        barrier.wait(timeout=10)
        response = client.patch(
            f"/api/v1/me/bookmarks/{annotation.pk}/",
            {
                "expected_updated_at": annotation.updated_at.isoformat(),
                "note": "সমান্তরাল লেখা",
            },
            format="json",
        )
        return response.status_code
    finally:
        connections.close_all()


def test_only_one_concurrent_note_edit_saves_at_the_same_revision(reader):
    _, user, book, _, publication = reader
    annotation = Bookmark.objects.create(
        user=user, book=book, location="chapter:0:0", prepared_publication=publication
    )
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(edit_at_revision, user, annotation, barrier)
            for _ in range(2)
        ]
        results = [future.result(timeout=15) for future in futures]
    assert sorted(results) == [200, 409]
    annotation.refresh_from_db()
    assert annotation.note == "সমান্তরাল লেখা"
