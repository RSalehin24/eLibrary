import zipfile

from apps.access.reading.preparation import prepare_epub_asset
from apps.catalog.models import GeneratedAsset, GeneratedAssetStatus, GeneratedAssetType

CONTAINER_XML = """<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/package.opf" /></rootfiles></container>"""
PACKAGE_XML = """<package xmlns="http://www.idpf.org/2007/opf">
<manifest>
<item id="one" href="chapter-1.xhtml" media-type="application/xhtml+xml" />
<item id="two" href="chapter-2.xhtml" media-type="application/xhtml+xml" />
<item id="css" href="styles.css" media-type="text/css" />
</manifest><spine><itemref idref="one" /><itemref idref="two" /></spine></package>"""


def write_epub(path, overrides=None):
    entries = {
        "mimetype": "application/epub+zip",
        "META-INF/container.xml": CONTAINER_XML,
        "OEBPS/package.opf": PACKAGE_XML,
        "OEBPS/chapter-1.xhtml": '<html><head><link rel="stylesheet" href="styles.css" /></head><body><h1>প্রথম অধ্যায়</h1><p>বাংলা বইয়ের প্রথম পাতা।</p></body></html>',
        "OEBPS/chapter-2.xhtml": "<html><body><h1>দ্বিতীয় অধ্যায়</h1><p>শেষ পাতা।</p></body></html>",
        "OEBPS/styles.css": "body { font-family: serif; }",
    }
    entries.update(overrides or {})
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return path


def prepared_asset(book, tmp_path):
    path = write_epub(tmp_path / f"{book.pk}.epub")
    asset = GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(path),
    )
    publication = prepare_epub_asset(asset)
    asset.refresh_from_db()
    return asset, publication
