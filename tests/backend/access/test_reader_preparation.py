import stat
import zipfile
from unittest.mock import patch
from xml.etree import ElementTree

import pytest
from apps.access.publication_models import PreparationState, PreparedPublication
from apps.access.reading import epub_archive
from apps.access.reading.epub_paths import InvalidEpub, referenced_path
from apps.access.reading.preparation import prepare_epub_asset, publication_directory
from apps.accounts.models import User
from apps.catalog.models import Book, GeneratedAsset, GeneratedAssetType, UserBook
from rest_framework.test import APIClient

from .reader_fixtures import PACKAGE_XML, write_epub

pytestmark = pytest.mark.django_db


@pytest.fixture
def unprepared(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    path = write_epub(tmp_path / "source.epub")
    book = Book.objects.create(title="EPUB যাচাই")
    asset = GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status="ready",
        legacy_path=str(path),
    )
    return asset, path


def test_identical_checksums_reuse_prepared_resources(unprepared):
    asset, _ = unprepared
    publication = prepare_epub_asset(asset)
    with patch("apps.access.reading.preparation.extract_publication") as extractor:
        repeated = prepare_epub_asset(asset)
    assert repeated.pk == publication.pk
    extractor.assert_not_called()
    assert PreparedPublication.objects.count() == 1
    assert (publication_directory(publication) / "OEBPS/chapter-1.xhtml").exists()


def test_preparation_updates_resources_from_an_older_safety_policy(unprepared):
    asset, _ = unprepared
    publication = prepare_epub_asset(asset)
    original_directory = publication_directory(publication)
    publication.manifest.pop("preparation_version")
    publication.save(update_fields=["manifest"])
    updated = prepare_epub_asset(asset)
    assert updated.pk == publication.pk
    assert updated.manifest["preparation_version"] == 1
    assert publication_directory(updated) != original_directory
    assert original_directory.is_dir()


@pytest.mark.parametrize(
    "path",
    ["../escape", "/escape", "OEBPS/../../escape", "OEBPS\\escape", "OEBPS/./chapter"],
)
def test_unsafe_archive_paths_never_publish(unprepared, path):
    asset, source = unprepared
    write_epub(source, {path: "unsafe"})
    with pytest.raises(InvalidEpub):
        prepare_epub_asset(asset)
    publication = PreparedPublication.objects.get()
    assert publication.state == PreparationState.FAILED
    assert not publication_directory(publication).exists()


def test_duplicate_archive_entries_are_rejected(unprepared):
    asset, source = unprepared
    with pytest.warns(UserWarning), zipfile.ZipFile(source, "a") as archive:
        archive.writestr("OEBPS/chapter-1.xhtml", "duplicate")
    with pytest.raises(InvalidEpub, match="duplicate"):
        prepare_epub_asset(asset)


def test_symbolic_links_are_rejected(unprepared):
    asset, source = unprepared
    link = zipfile.ZipInfo("OEBPS/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(source, "a") as archive:
        archive.writestr(link, "../../outside")
    with pytest.raises(InvalidEpub, match="special"):
        prepare_epub_asset(asset)


@pytest.mark.parametrize(
    "package",
    [
        PACKAGE_XML.replace("chapter-1.xhtml", "https://outside.test/chapter.xhtml"),
        '<!DOCTYPE package [<!ENTITY unsafe "expanded">]>' + PACKAGE_XML,
        PACKAGE_XML.replace(
            'media-type="text/css"', 'media-type="text/css&#13;&#10;Invalid"'
        ),
        PACKAGE_XML.replace('idref="one"', 'idref="missing"'),
    ],
)
def test_unsafe_or_invalid_package_metadata_is_rejected(unprepared, package):
    asset, source = unprepared
    write_epub(source, {"OEBPS/package.opf": package})
    with pytest.raises(InvalidEpub):
        prepare_epub_asset(asset)
    assert PreparedPublication.objects.get().state == PreparationState.FAILED


def test_extraction_limits_are_enforced(unprepared, monkeypatch):
    asset, _ = unprepared
    monkeypatch.setattr(epub_archive, "MAX_EXPANDED_BYTES", 100)
    with pytest.raises(InvalidEpub, match="expanded size"):
        prepare_epub_asset(asset)


def test_compression_bombs_are_rejected(unprepared):
    asset, source = unprepared
    with zipfile.ZipFile(source, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("OEBPS/large.txt", b"a" * 100_000)
    with pytest.raises(InvalidEpub, match="compression ratio"):
        prepare_epub_asset(asset)


def test_corrupt_archive_does_not_publish(unprepared):
    asset, source = unprepared
    source.write_bytes(b"invalid zip")
    with pytest.raises(InvalidEpub):
        prepare_epub_asset(asset)
    assert PreparedPublication.objects.get().state == PreparationState.FAILED


def test_preparation_removes_automatic_navigation_and_preserves_markup(unprepared):
    asset, source = unprepared
    document = '<?xml version="1.0"?><html><head><BASE href="https://external.test/" /><meta HTTP-EQUIV=" refresh " content="0;url=/api/"/><meta name="author" content="লেখক"/></head><body><svg viewBox="0 0 10 10"><clipPath id="clip"></clipPath></svg><p>বাংলা &amp; text</p></body></html>'
    write_epub(source, {"OEBPS/chapter-1.xhtml": document})
    publication = prepare_epub_asset(asset)
    prepared = (
        publication_directory(publication) / "OEBPS/chapter-1.xhtml"
    ).read_text()
    assert "BASE" not in prepared and "HTTP-EQUIV" not in prepared
    assert '<clipPath id="clip"></clipPath>' in prepared
    assert 'viewBox="0 0 10 10"' in prepared
    assert "বাংলা &amp; text" in prepared and 'name="author"' in prepared
    with patch("apps.access.reading.preparation.extract_publication") as extractor:
        prepare_epub_asset(asset)
    extractor.assert_not_called()


def test_paired_navigation_tags_are_removed_without_breaking_xhtml(unprepared):
    asset, source = unprepared
    document = '<html><head><base href="https://external.test/"></base><meta http-equiv="refresh" content="0;url=/api/"></meta><meta name="author" content="লেখক"></meta></head><body><p>পাঠ</p></body></html>'
    write_epub(source, {"OEBPS/chapter-1.xhtml": document})
    publication = prepare_epub_asset(asset)
    prepared = (
        publication_directory(publication) / "OEBPS/chapter-1.xhtml"
    ).read_bytes()
    parsed = ElementTree.fromstring(prepared)
    assert parsed.find("head/base") is None
    assert len(parsed.findall("head/meta")) == 1
    assert parsed.find("head/meta").attrib["name"] == "author"


def test_local_parent_references_are_resolved_within_archive():
    assert (
        referenced_path("OEBPS/text/package.opf", "../images/cover.jpg")
        == "OEBPS/images/cover.jpg"
    )
    with pytest.raises(InvalidEpub):
        referenced_path("OEBPS/package.opf", "../../escape")


def test_replacement_keeps_existing_reader_resources(unprepared, tmp_path):
    asset, _ = unprepared
    book = asset.book
    old_publication = prepare_epub_asset(asset)
    user = User.objects.create_user(email="replacement-reader@library.test")
    UserBook.objects.create(user=user, book=book)
    client = APIClient()
    client.force_authenticate(user)
    first = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    source = write_epub(
        tmp_path / "replacement.epub",
        {"OEBPS/chapter-1.xhtml": "<html><body>নতুন সংস্করণ</body></html>"},
    )
    asset.legacy_path = str(source)
    asset.save(update_fields=["legacy_path", "updated_at"])
    replacement = prepare_epub_asset(asset)
    assert replacement.pk != old_publication.pk
    second = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    assert first["id"] != second["id"]
    old_response = client.get(first["resource_base"] + "OEBPS/chapter-1.xhtml")
    assert "প্রথম পাতা" in b"".join(old_response.streaming_content).decode()
    new_response = client.get(second["resource_base"] + "OEBPS/chapter-1.xhtml")
    assert "নতুন সংস্করণ" in b"".join(new_response.streaming_content).decode()
