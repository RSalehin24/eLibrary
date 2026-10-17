import pytest
from apps.access.reading.preparation import prepare_epub_asset
from apps.catalog.models import Book, GeneratedAsset

from .reader_fixtures import PACKAGE_XML, write_epub

pytestmark = pytest.mark.django_db


def prepared_navigation(tmp_path, document, kind="nav"):
    package = PACKAGE_XML.replace(
        "</manifest>",
        '<item id="contents" href="contents.xml" media-type="'
        + ("application/xhtml+xml" if kind == "nav" else "application/x-dtbncx+xml")
        + ('" properties="nav"' if kind == "nav" else '"')
        + " /></manifest>",
    )
    path = write_epub(
        tmp_path / "navigation.epub",
        {"OEBPS/package.opf": package, "OEBPS/contents.xml": document},
    )
    asset = GeneratedAsset.objects.create(
        book=Book.objects.create(title="Contents"),
        asset_type="epub",
        legacy_path=str(path),
    )
    return prepare_epub_asset(asset).manifest


def test_epub3_contents_preserve_nested_headings_fragments_and_spine_targets(
    tmp_path, settings
):
    settings.MEDIA_ROOT = tmp_path / "media"
    document = """<?xml version="1.0"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body>
    <nav epub:type="landmarks"><ol><li><a href="chapter-2.xhtml">Ignore</a></li></ol></nav>
    <nav epub:type="toc"><h1>Contents</h1><ol><li><span>প্রথম পর্ব</span><ol>
    <li><a href="chapter-1.xhtml#%E0%A6%AA%E0%A6%BE%E0%A6%A0">প্রথম পাঠ</a></li>
    <li><a href="chapter-2.xhtml">দ্বিতীয় পাঠ</a></li></ol></li></ol></nav></body></html>"""
    manifest = prepared_navigation(tmp_path, document)
    assert manifest["navigation"] == [
        {"label": "প্রথম পর্ব", "chapter_index": None, "fragment": "", "depth": 0},
        {"label": "প্রথম পাঠ", "chapter_index": 0, "fragment": "পাঠ", "depth": 1},
        {"label": "দ্বিতীয় পাঠ", "chapter_index": 1, "fragment": "", "depth": 1},
    ]
    assert manifest["chapters"][1]["spine_index"] == 1
    assert manifest["chapters"][1]["idref"] == "two"


def test_epub2_ncx_contents_preserve_the_navigation_order_and_hierarchy(
    tmp_path, settings
):
    settings.MEDIA_ROOT = tmp_path / "media"
    document = """<?xml version="1.0"?><!DOCTYPE ncx PUBLIC "NCX" "https://outside.test/never-fetch.dtd"><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <navMap><navPoint><navLabel><text>Part Two</text></navLabel><content src="chapter-2.xhtml" />
    <navPoint><navLabel><text>A Section</text></navLabel><content src="chapter-2.xhtml#section" /></navPoint>
    </navPoint><navPoint><navLabel><text>Part One</text></navLabel><content src="chapter-1.xhtml" /></navPoint></navMap></ncx>"""
    navigation = prepared_navigation(tmp_path, document, "ncx")["navigation"]
    assert [
        (item["label"], item["chapter_index"], item["depth"]) for item in navigation
    ] == [("Part Two", 1, 0), ("A Section", 1, 1), ("Part One", 0, 0)]
    assert navigation[1]["fragment"] == "section"


@pytest.mark.parametrize(
    "href",
    [
        "https://outside.test/book",
        "javascript:alert(1)",
        "../../outside",
        "missing.xhtml",
        "chapter-1.xhtml?token=private",
    ],
)
def test_contents_never_expose_external_or_unprepared_targets(tmp_path, settings, href):
    settings.MEDIA_ROOT = tmp_path / "media"
    document = f'<html><nav role="doc-toc"><ol><li><a href="{href}">Invalid</a></li><li><a href="chapter-1.xhtml">Valid</a></li></ol></nav></html>'
    navigation = prepared_navigation(tmp_path, document)["navigation"]
    assert [item["label"] for item in navigation] == ["Valid"]


@pytest.mark.parametrize(
    "document",
    [
        '<!DOCTYPE html [<!ENTITY injected "unsafe">]><html>&injected;</html>',
        '<html><nav role="doc-toc"><ol><li><a href="chapter-1.xhtml">Broken',
    ],
)
def test_invalid_optional_contents_fall_back_to_the_readable_spine(
    tmp_path, settings, document
):
    settings.MEDIA_ROOT = tmp_path / "media"
    manifest = prepared_navigation(tmp_path, document)
    assert manifest["navigation"] == [] and len(manifest["chapters"]) == 2


@pytest.mark.parametrize("bound", ["MAX_NAVIGATION_DEPTH", "MAX_NAVIGATION_ENTRIES"])
def test_contents_limits_preserve_the_spine_instead_of_publishing_partial_navigation(
    tmp_path, monkeypatch, bound
):
    monkeypatch.setattr("django.conf.settings.MEDIA_ROOT", tmp_path / "media")
    monkeypatch.setattr(f"apps.access.reading.navigation.{bound}", 0)
    document = '<html><nav role="doc-toc"><ol><li><span>Part</span><ol><li><a href="chapter-1.xhtml">Chapter</a></li></ol></li></ol></nav></html>'
    manifest = prepared_navigation(tmp_path, document)
    assert manifest["navigation"] == [] and len(manifest["chapters"]) == 2
