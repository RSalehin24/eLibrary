from pathlib import Path

import pytest
from apps.catalog.models import GeneratedAsset
from bs4 import BeautifulSoup

from ..access.reader_fixtures import PACKAGE_XML, write_epub
from .epub_upload_fixtures import send_upload

pytestmark = pytest.mark.django_db


def test_upload_html_follows_spine_order_and_rewrites_ids_and_links(upload_book):
    path = upload_book[3]
    package = PACKAGE_XML.replace(
        '<itemref idref="one" /><itemref idref="two" />',
        '<itemref idref="two" /><itemref idref="one" />',
    )
    write_epub(
        path,
        {
            "OEBPS/package.opf": package,
            "OEBPS/chapter-1.xhtml": '<html><body><h1 id="same">First</h1><a href="chapter-2.xhtml#same">Previous</a></body></html>',
            "OEBPS/chapter-2.xhtml": '<html><body><h1 id="same">Second</h1><a href="chapter-1.xhtml#same">Next</a><table><tr><td>Cell</td></tr></table></body></html>',
        },
    )
    assert send_upload(upload_book).status_code == 200
    asset = GeneratedAsset.objects.get(book=upload_book[1], asset_type="html")
    soup = BeautifulSoup(Path(asset.file.path).read_bytes(), "html.parser")
    assert [node.get_text() for node in soup.select("h1")] == ["Second", "First"]
    assert [node["id"] for node in soup.select("h1")] == [
        "chapter-1--same",
        "chapter-2--same",
    ]
    assert [node["href"] for node in soup.select("a")] == [
        "#chapter-2--same",
        "#chapter-1--same",
    ]
    assert soup.select_one("table td").get_text() == "Cell"
    upload_book[1].refresh_from_db()
    assert upload_book[1].state == "published"


@pytest.mark.parametrize(
    "override",
    [
        {
            "OEBPS/chapter-1.xhtml": '<html><body><p>Text</p><script>fetch("https://example.test/")</script></body></html>'
        },
        {
            "OEBPS/chapter-1.xhtml": '<html><body><img src="https://example.test/image.png"></body></html>'
        },
        {"OEBPS/styles.css": 'body {background:url("../../outside.png")}'},
        {
            "OEBPS/chapter-2.xhtml": '<html><body><p>Text</p><iframe src="chapter-1.xhtml"></iframe></body></html>'
        },
    ],
)
def test_unsafe_or_unconvertible_epub_cannot_replace_any_active_file(
    upload_book, override
):
    assert send_upload(upload_book).status_code == 200
    before = list(
        GeneratedAsset.objects.order_by("asset_type").values(
            "asset_type", "checksum", "file"
        )
    )
    upload_book[1].refresh_from_db()
    revision = upload_book[1].updated_at
    write_epub(upload_book[3], override)
    response = send_upload(upload_book)
    assert response.status_code == 400 and response.json()["field_errors"]["file"]
    assert (
        list(
            GeneratedAsset.objects.order_by("asset_type").values(
                "asset_type", "checksum", "file"
            )
        )
        == before
    )
    upload_book[1].refresh_from_db()
    assert upload_book[1].updated_at == revision and upload_book[1].state == "published"
