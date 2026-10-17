from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.access.publication_models import PreparedPublication
from apps.access.reading.document_safety import PREPARATION_VERSION
from apps.accounts.models import User
from apps.catalog.models import GeneratedAsset
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def authenticated(actor):
    client = APIClient()
    client.force_authenticate(actor)
    return client


def assets_url(job):
    return f"/api/v1/manage/books/{job.book.slug}/assets/"


def download_url(asset):
    return f"/api/v1/manage/assets/{asset.pk}/download/"


def html_asset(job):
    asset = GeneratedAsset(book=job.book, asset_type="html", status="ready")
    asset.file.save("book.html", ContentFile(b"<!doctype html><h1>Book</h1>"))
    return asset


@pytest.mark.parametrize("kind", ["epub", "html"])
def test_manager_downloads_actual_draft_files_with_private_attachment_headers(
    preparation_job, kind, settings
):
    settings.PROTECTED_FILES_USE_NGINX = False
    asset = preparation_job.asset if kind == "epub" else html_asset(preparation_job)
    client = authenticated(preparation_job.requested_by)
    entries = client.get(assets_url(preparation_job)).json()
    entry = next(value for value in entries if value["id"] == str(asset.pk))
    assert entry["file_available"] and entry["download_url"] == download_url(asset)
    response = client.get(entry["download_url"])
    assert response.status_code == 200
    content = b"".join(response.streaming_content)
    assert content.startswith(b"PK" if kind == "epub" else b"<!doctype html>")
    assert response["Content-Type"].startswith(
        "application/epub+zip" if kind == "epub" else "text/html"
    )
    assert "attachment" in response["Content-Disposition"]
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Robots-Tag"] == "noindex"
    assert response["Content-Security-Policy"] == "sandbox"
    assert response["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize(
    "scopes", [[], [PermissionScope.DOWNLOAD_FILE], [PermissionScope.METADATA_EDIT]]
)
def test_download_requires_processing_authority(preparation_job, scopes):
    actor = User.objects.create_user(email="file-reader@example.test")
    for scope in scopes:
        PermissionGrant.objects.create(user=actor, scope=scope)
    client = authenticated(actor)
    assert client.get(download_url(preparation_job.asset)).status_code == 403
    assert client.get(assets_url(preparation_job)).status_code == 403


def test_processing_authority_alone_does_not_grant_file_access(preparation_job):
    actor = User.objects.create_user(email="file-processor@example.test")
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.PROCESSING_MANAGE)
    client = authenticated(actor)
    entry = client.get(assets_url(preparation_job)).json()[0]
    assert entry["file_available"] and entry["download_url"] is None
    assert client.get(download_url(preparation_job.asset)).status_code == 403
    PermissionGrant.objects.create(
        user=actor, book=preparation_job.book, scope=PermissionScope.DOWNLOAD_FILE
    )
    allowed = client.get(download_url(preparation_job.asset))
    assert allowed.status_code == 200
    assert b"".join(allowed.streaming_content).startswith(b"PK")
    actor.is_active = False
    actor.save()
    assert client.get(download_url(preparation_job.asset)).status_code == 403


def test_missing_and_failed_files_never_offer_a_download(preparation_job):
    asset = preparation_job.asset
    asset.file = ""
    asset.legacy_path = "/not-present/library.epub"
    asset.save()
    client = authenticated(preparation_job.requested_by)
    entry = client.get(assets_url(preparation_job)).json()[0]
    assert entry["file_available"] is False and entry["download_url"] is None
    assert client.get(download_url(asset)).status_code == 404
    asset.status = "failed"
    asset.save()
    assert client.get(download_url(asset)).status_code == 404
    assert client.get(f"/api/v1/manage/assets/{uuid4()}/download/").status_code == 404


def test_removed_books_cannot_be_downloaded(preparation_job):
    preparation_job.book.deleted_at = timezone.now()
    preparation_job.book.save()
    client = authenticated(preparation_job.requested_by)
    assert client.get(download_url(preparation_job.asset)).status_code == 404
    assert client.get(assets_url(preparation_job)).status_code == 404


def test_nginx_download_preserves_html_type_and_protected_storage(
    preparation_job, settings
):
    settings.PROTECTED_FILES_USE_NGINX = True
    asset = html_asset(preparation_job)
    response = authenticated(preparation_job.requested_by).get(download_url(asset))
    assert response.status_code == 200 and response["Content-Type"] == "text/html"
    assert response["X-Accel-Redirect"].startswith("/_protected/")
    assert "attachment" in response["Content-Disposition"]


def test_preparation_state_distinguishes_existing_file_from_online_readiness(
    preparation_job,
):
    client = authenticated(preparation_job.requested_by)
    entry = client.get(assets_url(preparation_job)).json()[0]
    assert entry["file_available"] and not entry["reader_ready"]
    assert entry["active_preparation_id"] == str(preparation_job.pk)
    PreparedPublication.objects.create(
        checksum=preparation_job.asset.checksum,
        state="ready",
        manifest={"preparation_version": PREPARATION_VERSION},
    )
    assert client.get(assets_url(preparation_job)).json()[0]["reader_ready"]
