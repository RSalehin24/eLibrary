from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile

import pytest
from apps.ingestion.source_processing.storage import source_job_directory
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from regeneration_fixtures import request_regeneration
from rest_framework.test import APIClient
from source_processing_fixtures import curated_source, execute_source_job

pytestmark = pytest.mark.django_db


def image_bytes(color):
    content = BytesIO()
    Image.new("RGB", (30, 40), color).save(content, "PNG")
    return content.getvalue()


@pytest.mark.parametrize("removed", [False, True])
def test_source_regeneration_preserves_an_explicit_cover_choice(
    regeneration, monkeypatch, removed
):
    actor, book, _, asset, _ = regeneration
    client = APIClient()
    client.force_authenticate(actor)
    path = f"/api/v1/manage/books/{book.slug}/cover/"
    previous = image_bytes("green")
    response = client.post(
        path,
        {
            "expected_updated_at": book.updated_at.isoformat(),
            "image": SimpleUploadedFile("chosen.png", previous, "image/png"),
        },
        format="multipart",
    )
    assert response.status_code == 200
    book.refresh_from_db()
    checksum = book.metadata_overrides["cover"]
    if removed:
        response = client.delete(
            path, {"expected_updated_at": book.updated_at.isoformat()}, format="json"
        )
        assert response.status_code == 200
        book.refresh_from_db()
    job = request_regeneration(regeneration)
    directory = source_job_directory(job.pk)
    source_image = image_bytes("blue")
    (directory / "source-cover.png").write_bytes(source_image)
    result = curated_source(directory)
    result["projection"]["cover"] = "source-cover.png"
    result["document"]["projection"]["cover"] = "source-cover.png"
    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.curate_source_job",
        lambda ownership, current: (result, current.checkpoint),
    )
    execute_source_job(job)
    assert job.state == "succeeded", job.error_code
    book.refresh_from_db()
    covers = book.generated_assets.filter(asset_type="cover")
    assert covers.exists() is not removed
    if not removed:
        assert covers.get().checksum == checksum
    assert book.metadata_overrides["cover"] == (None if removed else checksum)
    asset.refresh_from_db()
    with asset.file.open("rb") as content, ZipFile(content) as archive:
        images = [
            archive.read(name)
            for name in archive.namelist()
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ]
    assert source_image not in images
    assert any(sha256(image).hexdigest() == checksum for image in images) is not removed
