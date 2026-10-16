import io
from pathlib import Path
from unittest.mock import patch

import pytest
from apps.accounts.models import User
from apps.accounts.profile_images import normalized_profile_image, replace_profile_image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from PIL import Image, PngImagePlugin
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
URL = "/api/v1/auth/profile/image/"


@pytest.fixture
def image_account(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user(email="image-reader@library.test")
    client = APIClient()
    client.force_authenticate(user)
    return user, client, tmp_path


def image_upload(size=(800, 600)):
    output = io.BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", "private-source-metadata")
    Image.new("RGB", size, "blue").save(output, format="PNG", pnginfo=metadata)
    return SimpleUploadedFile(
        "../../untrusted.svg", output.getvalue(), content_type="image/svg+xml"
    )


def test_profile_images_are_normalized_private_and_do_not_invalidate_sessions(
    image_account,
):
    user, client, _ = image_account
    session_hash = user.get_session_auth_hash()
    response = client.post(
        URL,
        {"expected_updated_at": user.updated_at.isoformat(), "image": image_upload()},
        format="multipart",
    )
    assert response.status_code == 200
    url = response.json()["profile_image_url"]
    assert url.startswith(URL) and "/media/" not in url
    user.refresh_from_db()
    assert user.get_session_auth_hash() == session_hash
    with Image.open(user.profile_image.path) as result:
        assert result.format == "PNG" and max(result.size) == 512
        assert "Comment" not in result.info
    assert client.get(URL)["Content-Type"] == "image/png"
    assert client.get(URL)["Cache-Control"] == "private, no-store"
    assert (
        client.get("/api/v1/auth/session/").json()["user"]["profile_image_url"] == url
    )
    assert APIClient().get(URL).status_code == 403
    client.force_authenticate(User.objects.create_user(email="no-image@library.test"))
    assert client.get(URL).status_code == 404


def test_replacing_and_removing_images_delete_old_files_only_after_commit(
    image_account, django_capture_on_commit_callbacks
):
    user, client, _ = image_account
    client.post(
        URL,
        {"expected_updated_at": user.updated_at.isoformat(), "image": image_upload()},
        format="multipart",
    )
    user.refresh_from_db()
    old = Path(user.profile_image.path)
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            URL,
            {
                "expected_updated_at": user.updated_at.isoformat(),
                "image": image_upload(),
            },
            format="multipart",
        )
        assert response.status_code == 200 and old.exists()
    assert not old.exists()
    user.refresh_from_db()
    current = Path(user.profile_image.path)
    with django_capture_on_commit_callbacks(execute=True):
        removed = client.delete(
            URL, {"expected_updated_at": user.updated_at.isoformat()}, format="json"
        )
        assert removed.status_code == 200 and current.exists()
    assert not current.exists() and removed.json()["profile_image_url"] == ""


def test_stale_image_commands_preserve_existing_file(image_account):
    user, client, _ = image_account
    revision = user.updated_at.isoformat()
    assert (
        client.post(
            URL,
            {"expected_updated_at": revision, "image": image_upload()},
            format="multipart",
        ).status_code
        == 200
    )
    user.refresh_from_db()
    path = user.profile_image.path
    assert (
        client.post(
            URL,
            {"expected_updated_at": revision, "image": image_upload()},
            format="multipart",
        ).status_code
        == 409
    )
    assert (
        client.delete(URL, {"expected_updated_at": revision}, format="json").status_code
        == 409
    )
    user.refresh_from_db()
    assert user.profile_image.path == path and Path(path).exists()


@pytest.mark.parametrize("kind", ["text", "too_large", "too_many_pixels", "animated"])
def test_invalid_profile_image_uploads_leave_profile_unchanged(image_account, kind):
    user, client, root = image_account
    upload = SimpleUploadedFile("unsafe.html", b"<script>bad</script>")
    if kind == "too_large":
        upload = SimpleUploadedFile("large.png", b"x" * (5 * 1024 * 1024 + 1))
    elif kind == "too_many_pixels":
        upload = image_upload((2049, 10))
    elif kind == "animated":
        output = io.BytesIO()
        Image.new("RGB", (8, 8), "blue").save(
            output,
            format="GIF",
            save_all=True,
            append_images=[Image.new("RGB", (8, 8), "red")],
        )
        upload = SimpleUploadedFile("animated.gif", output.getvalue())
    response = client.post(
        URL,
        {"expected_updated_at": user.updated_at.isoformat(), "image": upload},
        format="multipart",
    )
    assert response.status_code == 400 and "image" in response.json()["field_errors"]
    user.refresh_from_db()
    assert not user.profile_image and not list(root.rglob("*.png"))


def test_image_storage_is_cleaned_when_database_save_fails(image_account):
    user, _, root = image_account
    command = {
        "expected_updated_at": user.updated_at,
        "image": normalized_profile_image(image_upload()),
    }
    with (
        patch.object(User, "save", side_effect=DatabaseError("synthetic save failure")),
        pytest.raises(DatabaseError),
    ):
        replace_profile_image(user, command)
    assert not list(root.rglob("*.png"))


def test_profile_image_mutations_require_session_csrf(image_account):
    user, _, _ = image_account
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    assert (
        client.post(
            URL,
            {
                "expected_updated_at": user.updated_at.isoformat(),
                "image": image_upload(),
            },
            format="multipart",
        ).status_code
        == 403
    )
