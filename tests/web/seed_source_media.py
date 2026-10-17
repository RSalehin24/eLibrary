from html import escape
from pathlib import Path

from apps.access.publication_models import PreparedPublication
from apps.access.reading.preparation import publication_directory
from apps.catalog.models import Book, GeneratedAsset
from bs4 import BeautifulSoup
from django.conf import settings
from PIL import Image


def create_source_media(reading_book):
    book = Book.objects.get(pk=reading_book["id"])
    asset = GeneratedAsset.objects.get(book=book, asset_type="epub")
    publication = PreparedPublication.objects.get(checksum=asset.checksum)
    directory = publication_directory(publication)
    body = "\n".join(
        chapter_body(directory / chapter["path"])
        for chapter in publication.manifest["chapters"]
    )
    book.main_content_html = body
    book.save(update_fields=["main_content_html", "updated_at"])
    folder = Path(settings.MEDIA_ROOT) / "protected" / "source-fixtures" / str(book.pk)
    folder.mkdir(parents=True, exist_ok=True)
    html_path = folder / "book.html"
    html_path.write_text(
        f"<!doctype html><html lang='bn'><head><meta charset='utf-8'>"
        f"<title>{escape(book.title)}</title></head><body>"
        f"<h1>{escape(book.title)}</h1>{body}</body></html>",
        encoding="utf-8",
    )
    cover_path = folder / "cover.png"
    Image.new("RGB", (120, 180), (23, 62, 53)).save(cover_path)
    for kind, path in (("html", html_path), ("cover", cover_path)):
        GeneratedAsset.objects.create(
            book=book, asset_type=kind, status="ready", legacy_path=str(path)
        )


def chapter_body(path):
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    return "\n".join(map(str, soup.find_all(["h1", "h2", "h3", "p"])))
