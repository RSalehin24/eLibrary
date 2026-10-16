from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from ebooklib import epub


def interruptible_asset():
    from apps.catalog.models import Book, GeneratedAsset

    book = Book.objects.create(title=f"কর্মী বাধার পরীক্ষা {uuid4().hex[:8]}")
    path = Path(settings.MEDIA_ROOT) / "protected" / f"{book.pk}.epub"
    path.parent.mkdir(parents=True, exist_ok=True)
    publication = epub.EpubBook()
    publication.set_identifier(str(book.pk))
    publication.set_title(book.title)
    publication.set_language("bn")
    chapters = [interruption_chapter(index) for index in range(100)]
    for chapter in chapters:
        publication.add_item(chapter)
    publication.spine = chapters
    publication.toc = chapters
    publication.add_item(epub.EpubNcx())
    publication.add_item(epub.EpubNav())
    epub.write_epub(str(path), publication)
    return GeneratedAsset.objects.create(
        book=book, asset_type="epub", status="ready", legacy_path=str(path)
    )


def interruption_chapter(index):
    chapter = epub.EpubHtml(
        title=f"অধ্যায় {index}", file_name=f"chapter-{index}.xhtml", lang="bn"
    )
    paragraphs = "".join(
        f"<p>স্বতন্ত্র পরীক্ষার অনুচ্ছেদ {sha256(f'{index}-{paragraph}'.encode()).hexdigest()}</p>"
        for paragraph in range(1000)
    )
    chapter.content = f"<html><body><h1>অধ্যায় {index}</h1>{paragraphs}</body></html>"
    return chapter
