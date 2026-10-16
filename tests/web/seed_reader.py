from pathlib import Path
from uuid import uuid4

from django.conf import settings
from ebooklib import epub


def create_reading_book(user):
    from apps.access.reading.preparation import prepare_epub_asset
    from apps.catalog.models import Book, GeneratedAsset, GeneratedAssetType, UserBook

    book = Book.objects.create(
        title=f"পড়ার পরীক্ষা {uuid4().hex[:8]}", state="published", review_state="approved"
    )
    path = (
        Path(settings.MEDIA_ROOT) / "protected" / "reader-fixtures" / f"{book.pk}.epub"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    write_reader_fixture(path)
    asset = GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status="ready",
        legacy_path=str(path),
    )
    prepare_epub_asset(asset)
    UserBook.objects.create(user=user, book=book)
    return {"id": str(book.pk), "slug": book.slug, "title": book.title}


def write_reader_fixture(path):
    publication = epub.EpubBook()
    publication.set_identifier(str(uuid4()))
    publication.set_title("পড়ার পরীক্ষার বই")
    publication.set_language("bn")
    chapters = []
    for number, title in enumerate(["প্রথম অধ্যায়", "দ্বিতীয় অধ্যায়"]):
        chapter = epub.EpubHtml(
            title=title, file_name=f"chapter-{number + 1}.xhtml", lang="bn"
        )
        paragraphs = "".join(
            f'<p id="paragraph-{index}">অনুচ্ছেদ {index}: বাংলা পাঠকের জন্য এই পরীক্ষার পাতাটি লেখা হয়েছে। বই পড়া, ভাবনা ও স্মৃতির গল্প এখানে চলতে থাকে।</p>'
            for index in range(60)
        )
        chapter.content = f'<html><body><h1>{title}</h1>{paragraphs}<a href="chapter-{2 - number}.xhtml">অন্য অধ্যায়ে যান</a><img src="/api/access/books/reader-network-canary/download/html/" alt="" /><script>window.readerScriptExecuted = true;</script></body></html>'
        publication.add_item(chapter)
        chapters.append(chapter)
    publication.spine = chapters
    publication.toc = chapters
    publication.add_item(epub.EpubNcx())
    publication.add_item(epub.EpubNav())
    epub.write_epub(str(path), publication)
