import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.access.reading.preparation import publication_directory
from apps.catalog.models import UserBook
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_embedded_audio_is_an_explicit_session_bound_resource_and_revocation_is_immediate(
    reader,
):
    client, user, book, _, publication = reader
    content = b"RIFFsynthetic-protected-audio"
    target = publication_directory(publication) / "OEBPS/voice.wav"
    target.write_bytes(content)
    publication.manifest["resources"].append(
        {"path": "OEBPS/voice.wav", "media_type": "audio/wav", "size": len(content)}
    )
    publication.save()
    UserBook.objects.filter(user=user, book=book).delete()
    grant = PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_DURABLE
    )
    session = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    path = session["resource_base"] + "OEBPS/voice.wav"
    response = client.get(path)
    assert response.status_code == 200 and response["Content-Type"] == "audio/wav"
    try:
        assert b"".join(response.streaming_content) == content
        ranged = client.get(path, HTTP_RANGE="bytes=4-12")
        assert ranged.status_code == 206
        assert b"".join(ranged.streaming_content) == content[4:13]
        assert response["Cache-Control"] == "private, no-store"
        assert APIClient().get(path).status_code == 403
        assert (
            client.get(session["resource_base"] + "OEBPS/undeclared.wav").status_code
            == 404
        )
        grant.is_active = False
        grant.save()
        assert client.get(path).status_code == 403
        assert client.get(path, HTTP_RANGE="bytes=0-1").status_code == 403
    finally:
        if "ranged" in locals():
            ranged.close()
        response.close()
