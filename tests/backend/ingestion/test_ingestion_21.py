"""Compatibility facade for the test_ingestion_21 modules."""
import zipfile
from pathlib import Path as _Path

from apps.catalog.management.commands.repair_source_site_metadata import repaired_opf_nav_spine
from apps.ingestion.pipeline.epub_properties.epub_builder import EpubBuilder
from apps.ingestion.services.normalization import (
    extract_main_content_segments,
    extract_front_matter_entries,
    normalize_scraped_book,
)
from apps.ingestion.services.resolution_support_metadata import split_display_title

_MODULE_DIR = _Path(__file__).with_name("test_ingestion_21_cases")
_MODULE_FILES = ("source_site_metadata_fidelity.py",)

for _module_file in _MODULE_FILES:
    _module_path = _MODULE_DIR / _module_file
    exec(compile(_module_path.read_text(encoding="utf-8"), str(_module_path), "exec"), globals())

del _Path, _MODULE_DIR, _MODULE_FILES, _module_file, _module_path


def contributor_pairs(normalized):
    return {
        (entry["name"], entry["role"])
        for entry in normalized["contributors"]
    }


def test_title_suffixes_and_prose_are_not_contributors():
    assert split_display_title("আনন্দসঙ্গী – ২ ছোটগল্প") == (
        "আনন্দসঙ্গী – ২ ছোটগল্প",
        "",
    )

    historical = normalize_scraped_book(
        {
            "book_title": "ঐতিহাসিক সমগ্র",
            "author": "হেমেন্দ্রকুমার রায়",
            "series": "",
            "book_type": "",
            "book_info": """
            <p>সংকলন – শোভন রায়</p>
            <p>প্রচ্ছদ – মানস চক্রবর্তী</p>
            <p>সে গোয়েন্দা-অ্যাডভেঞ্চার গল্প-কাহিনি…বিমল-কুমার-সুন্দরবাবুকে নিয়ে হোক, কি অনুবাদ সাহিত্য হোক, কী ইতিহাসের পাতা থেকে মণিমুক্তো তুলে আনাই হোক, হেমেন্দ্রকুমার রায় সব কলমেই সব্যসাচী।</p>
            """,
        }
    )

    assert contributor_pairs(historical) == {
        ("শোভন রায়", "editor"),
        ("মানস চক্রবর্তী", "cover_artist"),
        ("হেমেন্দ্রকুমার রায়", "author"),
    }


def test_translator_and_publisher_values_are_cleaned_to_names_only():
    normalized = normalize_scraped_book(
        {
            "book_title": "সোফির জগৎ",
            "author": "ইয়স্তেন গার্ডার, জি. এইচ. হাবীব",
            "series": "",
            "book_type": "",
            "book_info": """
            <p>সোফির জগৎ – ইয়স্তেন গার্ডার – অনুবাদ : জি. এইচ. হাবীব / পাশ্চাত্য দর্শনের ইতিহাস নির্ভর এক অসাধারণ, বহুল পঠিত উপন্যাস</p>
            <p>প্রকাশক – ঐতিহ্য</p>
            """,
        }
    )

    assert contributor_pairs(normalized) == {
        ("জি. এইচ. হাবীব", "translator"),
        ("ঐতিহ্য", "publisher"),
        ("ইয়স্তেন গার্ডার", "author"),
    }


def test_lowercase_english_prose_is_not_a_translator_name():
    normalized = normalize_scraped_book(
        {
            "book_title": "Bad Translator Fixture",
            "author": "Valid Writer",
            "series": "",
            "book_type": "",
            "book_info": "<p>অনুবাদ : and elaborate purports</p>",
        }
    )

    assert contributor_pairs(normalized) == {("Valid Writer", "author")}

    titlecase_prose = normalize_scraped_book(
        {
            "book_title": "Bad Reader Fixture",
            "author": "Valid Writer",
            "series": "",
            "book_type": "",
            "book_info": "<p>অনুবাদ : Readers Ways</p>",
        }
    )

    assert contributor_pairs(titlecase_prose) == {("Valid Writer", "author")}


def test_first_edition_line_is_extracted_as_book_detail():
    entries = extract_front_matter_entries("<p>প্রথম সংস্করণ: বৈশাখ ১৩৮২</p>")

    assert entries == [
        {
            "key": "edition",
            "label": "প্রথম সংস্করণ",
            "value": "বৈশাখ ১৩৮২",
            "role": "",
            "roles": [],
        }
    ]


def test_source_generated_toc_container_is_removed_from_book_content():
    _, _, cleaned_content = extract_main_content_segments(
        """
        <div>
          <div class="ftwp-in-post ftwp-float-right" id="ftwp-container-outer">
            <div id="ftwp-container">
              <nav id="ftwp-contents"><h3>সূচিপত্র</h3><ol><li>ভুয়া সূচি</li></ol></nav>
            </div>
          </div>
          <p>মূল বইয়ের লেখা</p>
        </div>
        """
    )

    assert "ftwp" not in cleaned_content
    assert "ভুয়া সূচি" not in cleaned_content
    assert "মূল বইয়ের লেখা" in cleaned_content


def test_repair_opf_nav_spine_moves_navigation_after_cover():
    old_opf = """
    <package>
      <spine toc="ncx">
        <itemref idref="nav"/>
        <itemref idref="chapter_0"/>
        <itemref idref="chapter_1"/>
      </spine>
    </package>
    """

    repaired, changed = repaired_opf_nav_spine(old_opf)

    assert changed is True
    spine = repaired.split("<spine", 1)[1]
    first_itemref = spine.split("<itemref", 1)[1].split("/>", 1)[0]
    assert 'idref="nav"' not in first_itemref
    assert '<itemref idref="nav" linear="no"/>' in repaired


def test_epub_builder_sanitizes_title_filenames_and_keeps_nav_out_of_start(tmp_path):
    builder = EpubBuilder(
        book_title="তিন গোয়েন্দা ভলিউম ৪/১",
        author="রকিব হাসান",
        output_folder=str(tmp_path),
    )
    builder.add_title_page()
    builder.add_lesson_pages(
        [{"title": "প্রথম", "path": ["প্রথম"], "content": "<p>মূল লেখা</p>"}]
    )
    builder.build_epub(
        "তিন গোয়েন্দা ভলিউম ৪/১.epub",
        toc_structure=[{"title": "প্রথম", "path": ["প্রথম"]}],
    )

    epub_path = tmp_path / "তিন গোয়েন্দা ভলিউম ৪_১.epub"
    assert epub_path.exists()

    with zipfile.ZipFile(epub_path) as archive:
        opf_text = archive.read("EPUB/content.opf").decode("utf-8")

    first_itemref = opf_text.split("<spine", 1)[1].split("<itemref", 1)[1]
    assert 'idref="nav"' not in first_itemref.split("/>", 1)[0]
