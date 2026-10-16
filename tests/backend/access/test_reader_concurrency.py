from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from apps.access.models import (
    BookOpeningRecord,
    PermissionGrant,
    PermissionScope,
    PreviewAccessSession,
)
from apps.accounts.models import User
from apps.catalog.models import Book, GeneratedAsset, GeneratedAssetType
from django.db import close_old_connections, connections
from rest_framework.test import APIClient

from .reader_fixtures import prepared_asset

pytestmark = pytest.mark.django_db(transaction=True)


def launch_at_barrier(user, path, barrier):
    close_old_connections()
    try:
        client = APIClient()
        client.force_authenticate(user)
        barrier.wait(timeout=10)
        response = (
            client.get(path) if path.endswith("download/html/") else client.post(path)
        )
        return response.status_code
    finally:
        connections.close_all()


@pytest.mark.parametrize("other_opening", ["legacy", "versioned", "html"])
def test_concurrent_openings_consume_read_once_exactly_once(
    other_opening, tmp_path, settings
):
    settings.MEDIA_ROOT = tmp_path / "media"
    user = User.objects.create_user(email="concurrent-reader@library.test")
    book = Book.objects.create(title="একবার পড়ার বই")
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_ONCE
    )
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.PREVIEW_HTML
    )
    prepared_asset(book, tmp_path)
    html = tmp_path / "preview.html"
    html.write_text("<html></html>")
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.HTML,
        status="ready",
        legacy_path=str(html),
    )
    legacy = f"/api/access/books/{book.slug}/reader-launch/"
    alternatives = {
        "legacy": legacy,
        "versioned": f"/api/v1/reading/books/{book.slug}/launch/",
        "html": f"/api/access/books/{book.slug}/download/html/",
    }
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(launch_at_barrier, user, path, barrier)
            for path in (legacy, alternatives[other_opening])
        ]
        results = [future.result(timeout=15) for future in futures]
    assert sorted(results) == [200, 403]
    assert BookOpeningRecord.objects.filter(user=user, book=book).count() == 1
    assert PreviewAccessSession.objects.filter(user=user, book=book).count() <= 1
