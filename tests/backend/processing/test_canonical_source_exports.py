from zipfile import ZipFile

import pytest
from apps.ingestion.pipeline.epub_book import create_epub
from apps.ingestion.pipeline.html_book import create_html_book
from apps.ingestion.source_processing.export_verification import (
    require_verified_exports,
)
from bs4 import BeautifulSoup


def source_payload(folder):
    body = (
        "<p>বইয়ের প্রারম্ভিক আলোচনা ও লেখকের বিস্তারিত বক্তব্য।</p>"
        "<h2>একটি প্রশ্নের উত্তর</h2>"
        "<p>বক্তব্যের মধ্যে উদ্ধৃত বাক্যটি মূল লেখার অংশ হিসেবে থাকবে।</p>"
        "<h2>পরের অনুচ্ছেদের ব্যাখ্যা</h2>"
        "<p>অধ্যায় অনুমান করে মূল লেখার মাঝখানে নতুন সূচিপত্র ঢোকানো যাবে না।</p>"
    )
    return {
        "book_title": "সংরক্ষিত মূল পাঠ",
        "author": "পরীক্ষার লেখক",
        "series": "",
        "book_type": "প্রবন্ধ",
        "cover": "",
        "main_content": body,
        "book_info": "",
        "dedication": "",
        "toc": [],
        "content_items": [],
        "output_folder": str(folder),
    }


@pytest.mark.parametrize("canonical_key", ["canonical_sections", "canonical_manifest"])
def test_canonical_single_flow_keeps_source_text_contiguous_in_both_exports(
    tmp_path, canonical_key
):
    payload = source_payload(tmp_path)
    sections = [{"section_type": "body", "html": payload["main_content"]}]
    payload[canonical_key] = (
        sections if canonical_key == "canonical_sections" else {"version": "test"}
    )
    create_html_book(payload)
    create_epub(payload)
    path = tmp_path / f"{payload['book_title']}.epub"
    require_verified_exports(
        {"document": {"sections": sections}},
        {"html": tmp_path / "book.html", "epub": path},
    )
    with ZipFile(path) as archive:
        assert any(name.endswith("main_content.xhtml") for name in archive.namelist())
        assert not any(
            "lesson_" in name and name.endswith(".xhtml") for name in archive.namelist()
        )


def test_noncanonical_single_flow_retains_legacy_chapter_inference(tmp_path):
    payload = source_payload(tmp_path)
    create_epub(payload)
    with ZipFile(tmp_path / f"{payload['book_title']}.epub") as archive:
        assert (
            sum(
                "lesson_" in name and name.endswith(".xhtml")
                for name in archive.namelist()
            )
            >= 2
        )


def test_canonical_explicit_nested_contents_remains_authoritative(tmp_path):
    payload = source_payload(tmp_path)
    payload["main_content"] = ""
    items = [
        {
            "title": title,
            "type": "lesson",
            "path": ["মূল খণ্ড", title],
            "content": f"<p>{title} এর সম্পূর্ণ সংরক্ষিত পাঠ।</p>",
        }
        for title in ["প্রথম অংশ", "দ্বিতীয় অংশ"]
    ]
    payload["content_items"] = items
    payload["toc"] = [
        {
            "title": "মূল খণ্ড",
            "type": "section",
            "children": [
                {"title": item["title"], "type": "lesson", "path": item["path"]}
                for item in items
            ],
        }
    ]
    payload["canonical_sections"] = [
        {"section_type": "body", "html": item["content"]} for item in items
    ]
    create_html_book(payload)
    create_epub(payload)
    path = tmp_path / f"{payload['book_title']}.epub"
    require_verified_exports(
        {"document": {"sections": payload["canonical_sections"]}},
        {"html": tmp_path / "book.html", "epub": path},
    )
    with ZipFile(path) as archive:
        navigation = next(
            name for name in archive.namelist() if name.endswith("nav.xhtml")
        )
        document = BeautifulSoup(archive.read(navigation), "html.parser")
    parent = document.find("a", string="মূল খণ্ড").parent
    assert [
        item.get_text(" ", strip=True)
        for item in parent.find("ol").find_all("li", recursive=False)
    ] == ["প্রথম অংশ", "দ্বিতীয় অংশ"]
