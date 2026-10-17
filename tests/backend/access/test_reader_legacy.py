import pytest
from apps.access.models import Highlight
from apps.access.reading.preparation import prepare_epub_asset, publication_directory
from apps.processing.managed_assets import processing_assets

pytestmark = pytest.mark.django_db


def test_contents_updates_keep_existing_readers_available_and_preserve_old_files(
    reader,
):
    client, user, book, asset, publication = reader
    session = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    previous_directory = publication_directory(publication)
    publication.manifest.pop("manifest_version")
    publication.manifest.pop("navigation")
    publication.save()
    assert client.get(f"/api/v1/reading/sessions/{session['id']}/").status_code == 200
    info = processing_assets(book, user)[0]
    assert info.reader_ready and info.reader_update_available
    refreshed = prepare_epub_asset(asset)
    assert refreshed.pk == publication.pk and previous_directory.is_dir()
    assert refreshed.manifest["manifest_version"] == 2
    assert client.get(f"/api/v1/reading/sessions/{session['id']}/").status_code == 200
    info = processing_assets(book, user)[0]
    assert info.reader_ready and not info.reader_update_available


def test_legacy_cfi_highlights_remain_private_and_keep_their_original_location(reader):
    client, user, book, _, _ = reader
    cfi = "epubcfi(/4/2[one]!/4/4,/1:0,/1:4)"
    annotation = Highlight.objects.create(
        user=user,
        book=book,
        cfi_range=cfi,
        text="বাংলা",
        note="Original note",
        chapter_href="chapter-1.xhtml",
    )
    session = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    response = client.get(f"/api/v1/reading/sessions/{session['id']}/highlights/")
    assert (
        response.status_code == 200 and response["Cache-Control"] == "private, no-store"
    )
    data = response.json()["entries"][0]
    assert data["legacy_cfi"] == cfi and data["selector"] is None
    assert data["note"] == "Original note"
    annotation.refresh_from_db()
    assert annotation.cfi_range == cfi and annotation.prepared_publication_id is None


def test_current_text_selectors_do_not_become_legacy_cfis(reader):
    client, user, book, _, _ = reader
    Highlight.objects.create(
        user=user, book=book, cfi_range='{"start":0,"end":4}', text="বাংলা"
    )
    session = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    data = client.get(f"/api/v1/reading/sessions/{session['id']}/highlights/").json()[
        "entries"
    ][0]
    assert data["selector"] == {"start": 0, "end": 4} and data["legacy_cfi"] is None


def test_session_exposes_package_relative_paths_and_original_spine_identity(reader):
    client, _, book, _, _ = reader
    data = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    assert data["navigation"] == []
    assert [
        (item["href"], item["spine_index"], item["spine_step"], item["idref"])
        for item in data["chapters"]
    ] == [("chapter-1.xhtml", 0, 4, "one"), ("chapter-2.xhtml", 1, 4, "two")]
