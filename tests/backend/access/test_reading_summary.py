import pytest
from apps.access.models import PreviewAccessSession, ReadingSession
from apps.access.publication_models import PreparedPublication

pytestmark = pytest.mark.django_db


def launch(client, book):
    response = client.post(f"/api/v1/reading/books/{book.slug}/launch/")
    assert response.status_code == 200
    return response.json()


def test_reading_summary_identifies_the_session_that_saved_its_position(reader):
    client, user, book, _, publication = reader
    path = f"/api/v1/reading/books/{book.slug}/access/"
    assert client.get(path).json()["progress_session_id"] is None
    original = launch(client, book)
    newer = PreviewAccessSession.objects.create(
        user=user, book=book, prepared_publication=publication
    )
    progress = {"last_location": "chapter:1:0.4", "progress_percent": 70}
    response = client.put(
        f"/api/v1/reading/sessions/{original['id']}/progress/",
        progress,
        format="json",
    )
    assert response.status_code == 200
    summary = client.get(path).json()
    assert summary["active_session_id"] == str(newer.pk)
    assert summary["progress_session_id"] == original["id"]
    assert summary["reading_progress"] == progress
    detail = client.get(f"/api/v1/reading/sessions/{newer.pk}/").json()
    assert detail["progress_matches_edition"] is True
    response = client.put(
        f"/api/v1/reading/sessions/{newer.pk}/progress/", progress, format="json"
    )
    assert response.status_code == 200
    assert (
        ReadingSession.objects.get(user=user, book=book).preview_session_id == newer.pk
    )


def test_new_edition_cannot_claim_a_previous_editions_saved_position(reader):
    client, user, book, asset, publication = reader
    original = launch(client, book)
    new_publication = PreparedPublication.objects.create(
        checksum="b" * 64,
        state="ready",
        manifest={
            **publication.manifest,
            "chapters": [{"label": "New edition", "path": "new.xhtml"}],
        },
    )
    ReadingSession.objects.filter(user=user, book=book).update(
        last_location="chapter:1:0.4", progress_percent=70
    )
    asset.checksum = new_publication.checksum
    asset.save(update_fields=["checksum"])
    current = launch(client, book)
    summary = client.get(f"/api/v1/reading/books/{book.slug}/access/").json()
    assert summary["active_session_id"] == current["id"]
    assert current["id"] != original["id"]
    assert summary["progress_session_id"] == original["id"]
    assert current["progress_matches_edition"] is False
    assert current["reading_progress"] == {
        "last_location": "chapter:1:0.4",
        "progress_percent": 70,
    }
    assert (
        ReadingSession.objects.get(user=user, book=book).last_location
        == "chapter:1:0.4"
    )


def test_imported_positions_retain_the_readers_existing_structural_validation(reader):
    client, user, book, _, _ = reader
    ReadingSession.objects.create(
        user=user, book=book, last_location="chapter-2.xhtml#paragraph-40"
    )
    session = launch(client, book)
    assert session["progress_matches_edition"] is True
    assert ReadingSession.objects.get(user=user, book=book).preview_session_id is None


def test_quarantine_hides_session_provenance_without_erasing_personal_progress(reader):
    client, user, book, _, _ = reader
    launch(client, book)
    ReadingSession.objects.filter(user=user, book=book).update(
        last_location="chapter:0:0.4", progress_percent=20
    )
    book.source_quality_state = "quarantined"
    book.save(update_fields=["source_quality_state"])
    summary = client.get(f"/api/v1/reading/books/{book.slug}/access/").json()
    assert summary["active_session_id"] is None
    assert summary["progress_session_id"] is None
    assert summary["reading_progress"]["progress_percent"] == 20
