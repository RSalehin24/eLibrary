from apps.access.models import Bookmark, Highlight, ReadingSession
from apps.access.publication_models import PreparedPublication
from apps.catalog.models import GeneratedAsset
from ebooklib import epub
from seed_reader import create_reading_book


def customize_legacy_publication(publication, chapters):
    publication.toc = [
        (
            epub.Link("chapter-1.xhtml", "প্রথম অধ্যায়", "first"),
            [
                epub.Link(
                    "chapter-1.xhtml#paragraph-40", "প্রথম পর্বের অংশ", "first-section"
                ),
                epub.Link(
                    "chapter-2.xhtml#paragraph-40", "দ্বিতীয় পর্বের অংশ", "second-section"
                ),
            ],
        ),
        epub.Link("chapter-2.xhtml", "দ্বিতীয় অধ্যায়", "second"),
    ]
    chapters[0].content = chapters[0].content.replace(
        "অনুচ্ছেদ 40: বাংলা", "অনুচ্ছেদ 40: 🪷 ^ বাংলা"
    )


def create_legacy_reader_fixture(user):
    book = create_reading_book(user, customize_legacy_publication)
    asset = GeneratedAsset.objects.get(book_id=book["id"], asset_type="epub")
    publication = PreparedPublication.objects.get(checksum=asset.checksum)
    chapter = publication.manifest["chapters"][0]
    base = f"/{chapter['spine_step']}/{(chapter['spine_index'] + 1) * 2}[{chapter['idref']}]!"
    prefix, quote = "অনুচ্ছেদ 40: 🪷 ^ ", "বাংলা পাঠকের"
    start = len(prefix.encode("utf-16-le")) // 2
    assertion = prefix.replace("^", "^^") + ",বাংলা"
    cfi = f"epubcfi({base}/4/84[paragraph-40],/1:{start}[{assertion}],/1:{start + len(quote)})"
    point = f"epubcfi({base}/4/84[paragraph-40]/1:{start}[{assertion}])"
    Bookmark.objects.create(
        user=user,
        book_id=book["id"],
        location=point,
        label="CFI Bookmark",
        chapter_href=chapter["href"],
        chapter_label="প্রথম অধ্যায়",
    )
    for text, note in [
        (quote, "Preserved original note"),
        ("Text from a different edition", "Stale original note"),
    ]:
        Highlight.objects.create(
            user=user,
            book_id=book["id"],
            cfi_range=cfi,
            text=text,
            note=note,
            chapter_href=chapter["href"],
            chapter_label="প্রথম অধ্যায়",
        )
    ReadingSession.objects.create(
        user=user,
        book_id=book["id"],
        last_location="chapter-2.xhtml#paragraph-40",
        progress_percent=0,
    )
    return {"book": book, "quote": quote, "cfi": cfi, "point": point}
