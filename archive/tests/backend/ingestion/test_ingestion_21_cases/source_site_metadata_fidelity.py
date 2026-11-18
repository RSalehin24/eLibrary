import zipfile

import pytest

from apps.common.source_site_batch_audit import compare_source_report_to_production
from apps.common.source_site_semantic_audit import audit_scraped_book
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline import epub_book, html_book, scraper as legacy_scraper
from apps.ingestion.pipeline.epub_properties.epub_builder import EpubBuilder
from apps.ingestion.services.normalization import (
    dedupe_html_fragment_blocks,
    dedupe_structured_sections,
    extract_boundary_sections_from_content_items,
    extract_main_content_segments,
    extract_front_matter_entries,
    infer_structured_content_from_main_content,
    merge_front_matter_html_parts,
    normalize_scraped_book,
    prune_duplicate_main_content,
    split_leading_front_sections,
)
from apps.ingestion.services.normalization_support.metadata import (
    extract_contributor_evidence,
)
from apps.ingestion.services.resolution_support_metadata import (
    metadata_entry_defaults,
    parse_source_page_metadata,
    split_display_title,
    upsert_source_catalog_entry,
)


def test_split_display_title_is_conservative_about_hyphenated_titles_and_role_suffixes():
    assert split_display_title("আনা ফ্রাঙ্ক-এর ডায়েরি") == ("আনা ফ্রাঙ্ক-এর ডায়েরি", "")
    assert split_display_title(
        "গডফাদার – মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম"
    ) == (
        "গডফাদার",
        "মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম",
    )
    assert split_display_title("পিরানদেল্লোর গল্প – সম্পাদনা : বুদ্ধদেব বসু") == (
        "পিরানদেল্লোর গল্প",
        "সম্পাদনা : বুদ্ধদেব বসু",
    )


def test_extract_contributor_evidence_handles_exact_role_phrases_without_word_loss():
    translated = extract_contributor_evidence("অনুবাদ করেছেন – মো: রিয়াজ উদ্দিন খান")
    adapted = extract_contributor_evidence("রূপান্তর: শেখ আবদুল হাকিম")
    edited = extract_contributor_evidence("বুদ্ধদেব বসু সম্পাদিত")
    translated_with_prefix = extract_contributor_evidence("অনুবাদ – মো: রিয়াজ উদ্দিন খান")
    publisher = extract_contributor_evidence("প্রকাশক শ্রীসনৎকুমার গুপ্ত বঙ্গীয়-সাহিত্য-পরিষৎ")
    english_publisher = extract_contributor_evidence("Published by ATMAJAA PUBLISHERS")
    english_editor = extract_contributor_evidence("Edited by Moheul Islam Mithu")
    inline_english_publisher = extract_contributor_evidence(
        "SRI RAMAKRISHNA O SAMAKALIN KOLKATA by Avijit Pal Published by ATMAJAA PUBLISHERS"
    )
    inline_english_editor = extract_contributor_evidence(
        "Arsen Lupin Gentleman Burgler by Maurice Leblanc Edited by Moheul Islam Mithu"
    )
    english_byline_with_addressed_publisher = extract_contributor_evidence(
        "RABIN HOOD by Hemendra Kumar Roy Published by PATRA BHARATI at 3/1 College Row, Kolkata 700009"
    )
    role_only = extract_contributor_evidence("মূল কিতাব পরিমার্জন ও সম্পাদনায়")
    role_mixed_prose = extract_contributor_evidence(
        "অশীন দাশগুপ্ত সহযোগী সম্পাদক রুদ্রাংশু মুখোপাধ্যায়"
    )
    committee_role = extract_contributor_evidence(
        "বিভাগ (সদস্য সচিব)",
        default_roles=["editor"],
    )
    committee_only = extract_contributor_evidence("সম্পাদনা পরিষদ")
    dated_location = extract_contributor_evidence("ঢাকা, বাংলাদেশ ২২/০৭/২২")
    numeric_only = extract_contributor_evidence("১")
    dangling_translator = extract_contributor_evidence("অনুবাদ: সালমান হক)")
    incomplete_name = extract_contributor_evidence("মো")

    assert translated["contributors"] == [
        {
            "name": "মো: রিয়াজ উদ্দিন খান",
            "role": "translator",
            "raw_value": "অনুবাদ করেছেন – মো: রিয়াজ উদ্দিন খান",
        }
    ]
    assert adapted["contributors"] == [
        {
            "name": "শেখ আবদুল হাকিম",
            "role": "translator",
            "raw_value": "রূপান্তর: শেখ আবদুল হাকিম",
        }
    ]
    assert edited["contributors"] == [
        {
            "name": "বুদ্ধদেব বসু",
            "role": "editor",
            "raw_value": "বুদ্ধদেব বসু সম্পাদিত",
        }
    ]
    assert translated_with_prefix["contributors"] == [
        {
            "name": "মো: রিয়াজ উদ্দিন খান",
            "role": "translator",
            "raw_value": "অনুবাদ – মো: রিয়াজ উদ্দিন খান",
        }
    ]
    assert publisher["contributors"] == [
        {
            "name": "শ্রীসনৎকুমার গুপ্ত বঙ্গীয়-সাহিত্য-পরিষৎ",
            "role": "publisher",
            "raw_value": "প্রকাশক শ্রীসনৎকুমার গুপ্ত বঙ্গীয়-সাহিত্য-পরিষৎ",
        }
    ]
    assert english_publisher["contributors"] == [
        {
            "name": "ATMAJAA PUBLISHERS",
            "role": "publisher",
            "raw_value": "Published by ATMAJAA PUBLISHERS",
        }
    ]
    assert english_editor["contributors"] == [
        {
            "name": "Moheul Islam Mithu",
            "role": "editor",
            "raw_value": "Edited by Moheul Islam Mithu",
        }
    ]
    assert inline_english_publisher["contributors"] == [
        {
            "name": "Avijit Pal",
            "role": "author",
            "raw_value": "SRI RAMAKRISHNA O SAMAKALIN KOLKATA by Avijit Pal Published by ATMAJAA PUBLISHERS",
        },
        {
            "name": "ATMAJAA PUBLISHERS",
            "role": "publisher",
            "raw_value": "SRI RAMAKRISHNA O SAMAKALIN KOLKATA by Avijit Pal Published by ATMAJAA PUBLISHERS",
        }
    ]
    assert inline_english_editor["contributors"] == [
        {
            "name": "Maurice Leblanc",
            "role": "author",
            "raw_value": "Arsen Lupin Gentleman Burgler by Maurice Leblanc Edited by Moheul Islam Mithu",
        },
        {
            "name": "Moheul Islam Mithu",
            "role": "editor",
            "raw_value": "Arsen Lupin Gentleman Burgler by Maurice Leblanc Edited by Moheul Islam Mithu",
        }
    ]
    assert english_byline_with_addressed_publisher["contributors"] == [
        {
            "name": "Hemendra Kumar Roy",
            "role": "author",
            "raw_value": "RABIN HOOD by Hemendra Kumar Roy Published by PATRA BHARATI at 3/1 College Row, Kolkata 700009",
        },
        {
            "name": "PATRA BHARATI",
            "role": "publisher",
            "raw_value": "RABIN HOOD by Hemendra Kumar Roy Published by PATRA BHARATI at 3/1 College Row, Kolkata 700009",
        },
    ]
    assert role_only["contributors"] == []
    assert role_only["authors"] == []
    assert role_mixed_prose["contributors"] == []
    assert role_mixed_prose["authors"] == []
    assert committee_role["contributors"] == []
    assert committee_role["authors"] == []
    assert committee_only["contributors"] == []
    assert committee_only["authors"] == []
    assert dated_location["contributors"] == []
    assert dated_location["authors"] == []
    assert numeric_only["contributors"] == []
    assert numeric_only["authors"] == []
    assert incomplete_name["contributors"] == []
    assert incomplete_name["authors"] == []
    assert dangling_translator["contributors"] == [
        {
            "name": "সালমান হক",
            "role": "translator",
            "raw_value": "অনুবাদ: সালমান হক)",
        }
    ]


def test_front_matter_and_weak_author_resolution_preserve_exact_names_and_roles():
    book_info_html = """
    <p><strong>অনুবাদ করেছেন</strong> – মো: রিয়াজ উদ্দিন খান)</p>
    <p><strong>অনুবাদ ও সম্পাদনা</strong> – বুদ্ধদেব বসু</p>
    <p><strong>প্রথম প্রকাশ</strong>: মার্চ ২০২৩</p>
    <p><strong>প্রকাশক</strong>: উত্তর প্রকাশনী)</p>
    """

    entries = extract_front_matter_entries(book_info_html)
    normalized = normalize_scraped_book(
        {
            "book_title": "গডফাদার",
            "author": "মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম",
            "series": "",
            "book_type": "",
            "book_info": book_info_html,
        }
    )

    assert entries[0]["value"] == "মো: রিয়াজ উদ্দিন খান"
    assert entries[1]["roles"] == ["translator", "editor"]
    assert {entry["key"]: entry["value"] for entry in entries if not entry["role"]} == {
        "first_published": "মার্চ ২০২৩",
    }

    contributor_roles = {
        (entry["name"], entry["role"])
        for entry in normalized["contributors"]
    }
    assert ("মারিয়ো পুজো", "author") in contributor_roles
    assert ("শেখ আবদুল হাকিম", "translator") in contributor_roles
    assert ("মো: রিয়াজ উদ্দিন খান", "translator") in contributor_roles
    assert ("বুদ্ধদেব বসু", "translator") in contributor_roles
    assert ("বুদ্ধদেব বসু", "editor") in contributor_roles
    assert ("উত্তর প্রকাশনী", "publisher") in contributor_roles
    assert not any("করেছেন" in entry["name"] for entry in normalized["contributors"])
    assert not any(entry["name"].endswith(")") for entry in normalized["contributors"])


def test_front_matter_line_breaks_do_not_create_ambiguous_publishers_or_role_fragments():
    addressed_publisher_case = normalize_scraped_book(
        {
            "book_title": "RABIN HOOD",
            "author": "Hemendra Kumar Roy",
            "series": "",
            "book_type": "",
            "book_info": """
            <p>RABIN HOOD by Hemendra Kumar Roy<br/>
            Published by PATRA BHARATI at 3/1 College Row,<br/>
            Kolkata 700009</p>
            """,
        }
    )
    publisher_case = normalize_scraped_book(
        {
            "book_title": "হ্যারেৎজ",
            "author": "অভীক মুখোপাধ্যায়",
            "series": "",
            "book_type": "",
            "book_info": """
            <p>প্রথম প্রকাশ জানুয়ারি ২০২০</p>
            <p>প্রচ্ছদ স্বর্ণাভ বেরা<br/>প্রকাশক অভিষেক আইচ ও অরিজিৎ ভদ্র দ্য কাফে টেবল</p>
            """,
        }
    )
    illustrator_case = normalize_scraped_book(
        {
            "book_title": "দ্য নেম অব দ্য গেম ইজ অ্যা কিডন্যাপিং",
            "author": "কেইগো হিগাশিনো",
            "series": "",
            "book_type": "",
            "book_info": """
            <p>অনুবাদ : বিমুগ্ধ সরকার রক্তিম<br/>
            ভূমিপ্রকাশের পক্ষে জাকির হোসেন কর্তৃক প্রকাশিত<br/>
            প্রথম প্রকাশ: আশ্বিন ১৪২৭, সেপ্টেম্বর ২০২০<br/>
            প্রচ্ছদ: সজল চৌধুরী<br/>
            অলংকরণ ও অক্ষরবিন্যাস: ভূমি ডেস্ক<br/>
            বানান সংশোধন ও বর্ণ অলংকরণ: জাকির হোসেন, সজল চৌধুরী</p>
            """,
        }
    )

    assert addressed_publisher_case["contributors"] == [
        {
            "name": "Hemendra Kumar Roy",
            "role": "author",
            "raw_value": "Hemendra Kumar Roy",
        },
        {
            "name": "PATRA BHARATI",
            "role": "publisher",
            "raw_value": "PATRA BHARATI at 3/1 College Row",
        },
    ]
    assert publisher_case["contributors"] == [
        {
            "name": "স্বর্ণাভ বেরা",
            "role": "cover_artist",
            "raw_value": "স্বর্ণাভ বেরা",
        },
        {
            "name": "অভীক মুখোপাধ্যায়",
            "role": "author",
            "raw_value": "অভীক মুখোপাধ্যায়",
        },
    ]
    assert illustrator_case["contributors"] == [
        {
            "name": "বিমুগ্ধ সরকার রক্তিম",
            "role": "translator",
            "raw_value": "বিমুগ্ধ সরকার রক্তিম",
        },
        {
            "name": "সজল চৌধুরী",
            "role": "cover_artist",
            "raw_value": "সজল চৌধুরী",
        },
        {
            "name": "জাকির হোসেন",
            "role": "illustrator",
            "raw_value": "জাকির হোসেন, সজল চৌধুরী",
        },
        {
            "name": "সজল চৌধুরী",
            "role": "illustrator",
            "raw_value": "জাকির হোসেন, সজল চৌধুরী",
        },
        {
            "name": "কেইগো হিগাশিনো",
            "role": "author",
            "raw_value": "কেইগো হিগাশিনো",
        },
    ]


def test_standalone_role_label_lines_carry_value_from_next_line_without_audit_false_positives():
    normalized = normalize_scraped_book(
        {
            "book_title": "পদ্মাবতী নাটক",
            "author": "মাইকেল মধুসূদন দত্ত",
            "series": "",
            "book_type": "",
            "book_info": """
            <p>সম্পাদক : ব্রজেন্দ্রনাথ বন্দ্যোপাধ্যায়, শ্রীসজনীকান্ত দাস</p>
            <p>প্রকাশক<br/>শ্রীসনৎকুমার গুপ্ত<br/>বঙ্গীয়-সাহিত্য-পরিষৎ</p>
            """,
        }
    )
    audit = audit_scraped_book(
        {
            "book_title": "আর্সেন লুপাঁ : জেন্টলম্যান বার্গলার",
            "author": "মরিস লেবলাঁ",
            "book_info": """
            <p>সম্পাদনা: মহিউল ইসলাম মিঠু</p>
            <p>প্রকাশকাল প্রথম প্রকাশ: আগস্ট, ২০২২</p>
            <p>Arsen Lupin Gentleman Burgler<br/>by Maurice Leblanc<br/>Edited by Moheul Islam Mithu</p>
            """,
            "main_content": "",
            "toc": [],
            "content_items": [],
        }
    )

    assert normalized["contributors"] == [
        {
            "name": "ব্রজেন্দ্রনাথ বন্দ্যোপাধ্যায়",
            "role": "editor",
            "raw_value": "ব্রজেন্দ্রনাথ বন্দ্যোপাধ্যায়, শ্রীসজনীকান্ত দাস",
        },
        {
            "name": "শ্রীসজনীকান্ত দাস",
            "role": "editor",
            "raw_value": "ব্রজেন্দ্রনাথ বন্দ্যোপাধ্যায়, শ্রীসজনীকান্ত দাস",
        },
        {
            "name": "শ্রীসনৎকুমার গুপ্ত",
            "role": "publisher",
            "raw_value": "শ্রীসনৎকুমার গুপ্ত",
        },
        {
            "name": "মাইকেল মধুসূদন দত্ত",
            "role": "author",
            "raw_value": "মাইকেল মধুসূদন দত্ত",
        },
    ]
    assert audit["missing_contributors"] == []
    assert audit["unsupported_contributors"] == []


def test_publisher_role_mentions_inside_prose_do_not_create_publishers():
    normalized = normalize_scraped_book(
        {
            "book_title": "মহাদেবী",
            "author": "অভীক সরকার",
            "series": "",
            "book_type": "",
            "book_info": """
            <p>প্রথম প্রকাশ – জানুয়ারি ২০২৪</p>
            <p>বইটি প্রকাশ করার জন্য প্রকাশক পত্রভারতীর কাছে আমার কৃতজ্ঞতার শেষ নেই। আশা করি ষড়যন্ত্র, নিষ্ঠুরতা, বীরত্ব, এবং সর্বোপরি মহৎ প্রেম ও অপ্রেমের এই গৌরবময় গাথাটি আপনাদের ভালো লাগবে।</p>
            """,
        }
    )

    assert normalized["contributors"] == [
        {
            "name": "অভীক সরকার",
            "role": "author",
            "raw_value": "অভীক সরকার",
        }
    ]


def test_publication_date_language_and_page_count_do_not_become_publishers():
    book_info = """
    <p><strong>কাগজের বউ – প্রেমের উপন্যাস – শীর্ষেন্দু মুখোপাধ্যায়</strong>।<br/>
    প্রকাশক: প্রথমা, প্রকাশকাল: বাংলা সন ১৩৮৪, ভাষা: বাংলা, বইয়ের পাতার সংখ্যা: ১০১</p>
    """

    entries = extract_front_matter_entries(book_info)
    normalized = normalize_scraped_book(
        {
            "book_title": "কাগজের বউ",
            "author": "শীর্ষেন্দু মুখােপাধ্যায়",
            "series": "",
            "book_type": "উপন্যাস",
            "book_info": book_info,
        }
    )

    entry_values = {entry["key"]: entry["value"].strip(" ,") for entry in entries}
    assert entry_values["publisher"] == "প্রথমা"
    assert entry_values["first_published"] == "বাংলা সন ১৩৮৪"
    assert entry_values["language"] == "বাংলা"
    assert entry_values["page_count"] == "১০১"
    assert normalized["contributors"] == [
        {
            "name": "প্রথমা",
            "role": "publisher",
            "raw_value": "প্রথমা",
        },
        {
            "name": "শীর্ষেন্দু মুখােপাধ্যায়",
            "role": "author",
            "raw_value": "শীর্ষেন্দু মুখােপাধ্যায়",
        },
    ]


def test_repeated_source_front_matter_blocks_are_deduped_before_export():
    first_block = "<p>প্রথম ই-বুক সংস্করণ জুন ২০২০<br/>প্রচ্ছদ – রোদ্দূর রায় ও ইভনিং সাগা</p>"
    publisher_block = "<p>প্রকাশক – স্বাতী রায়চৌধুরী</p>"
    section_html = "<p>রেনেসাঁবালগঙ্গাধরবাঁড়া</p><p>মূল ভূমিকা।</p><p>সপ্তর্ষি প্রকাশন</p>"
    trimmed_section_html = "<p>রেনেসাঁবালগঙ্গাধরবাঁড়া</p><p>মূল ভূমিকা।</p>"

    merged_info = merge_front_matter_html_parts(
        "\n".join([first_block, publisher_block]),
        "\n".join([first_block, publisher_block]),
    )
    deduped_dedication = dedupe_html_fragment_blocks(
        "<p>নবারুণ ভট্টাচার্য</p><p>নবারুণ ভট্টাচার্য</p>"
    )
    deduped_sections = dedupe_structured_sections(
        [
            {"title": "শুরুয়াৎ", "html": section_html},
            {"title": "শুরুয়াৎ", "html": trimmed_section_html},
        ],
        reference_fragments=[merged_info],
    )
    cleaned_main_content = prune_duplicate_main_content(
        "<p>সপ্তর্ষি প্রকাশন</p>",
        reference_fragments=[merged_info, deduped_dedication, section_html],
        content_items=[{"title": "প্রথম পাঠ", "content": "<p>content</p>"}],
    )

    assert merged_info.count("প্রথম ই-বুক সংস্করণ জুন ২০২০") == 1
    assert merged_info.count("স্বাতী রায়চৌধুরী") == 1
    assert deduped_dedication.count("নবারুণ ভট্টাচার্য") == 1
    assert [section["title"] for section in deduped_sections] == ["শুরুয়াৎ"]
    assert "সপ্তর্ষি প্রকাশন" not in deduped_sections[0]["html"]
    assert cleaned_main_content == ""


def test_infer_structured_content_from_main_content_builds_synthetic_toc_for_heading_only_books():
    toc, content_items, cleaned_main_content = infer_structured_content_from_main_content(
        """
        <div>
          <p>প্রারম্ভিক কথা</p>
          <h2>অধ্যায় ১</h2>
          <p>প্রথম অধ্যায়ের লেখা</p>
          <h2>অধ্যায় ২</h2>
          <p>দ্বিতীয় অধ্যায়ের লেখা</p>
        </div>
        """,
        book_title="উদাহরণ",
    )

    assert [entry["title"] for entry in toc] == ["অধ্যায় ১", "অধ্যায় ২"]
    assert [item["path"] for item in content_items] == [["অধ্যায় ১"], ["অধ্যায় ২"]]
    assert "প্রারম্ভিক কথা" in cleaned_main_content
    assert "প্রথম অধ্যায়ের লেখা" not in cleaned_main_content
    assert "দ্বিতীয় অধ্যায়ের লেখা" not in cleaned_main_content


def test_infer_structured_content_from_main_content_handles_loose_one_page_chapter_markers():
    toc, content_items, cleaned_main_content = infer_structured_content_from_main_content(
        """
        <div>
          <p>প্রচ্ছদ-নোট</p>
          <p><em>প্রথম অধ্যায়</em></p>
          <p>প্রথম অংশের বিস্তৃত লেখা।</p>
          <p><em>দ্বিতীয় অধ্যায়</em></p>
          <p>দ্বিতীয় অংশের বিস্তৃত লেখা।</p>
          <p><em>তৃতীয় অধ্যায়</em></p>
          <p>তৃতীয় অংশের বিস্তৃত লেখা।</p>
        </div>
        """,
        book_title="নমুনা",
    )

    assert [entry["title"] for entry in toc] == [
        "প্রথম অধ্যায়",
        "দ্বিতীয় অধ্যায়",
        "তৃতীয় অধ্যায়",
    ]
    assert [item["path"] for item in content_items] == [
        ["প্রথম অধ্যায়"],
        ["দ্বিতীয় অধ্যায়"],
        ["তৃতীয় অধ্যায়"],
    ]
    assert "প্রচ্ছদ-নোট" in cleaned_main_content
    assert "দ্বিতীয় অংশের বিস্তৃত লেখা।" not in cleaned_main_content


def test_infer_structured_content_from_main_content_handles_numeric_single_flow_books():
    toc, content_items, cleaned_main_content = infer_structured_content_from_main_content(
        """
        <div>
          <p>যে পথ দিয়ে সে চলে গেল, সেই পথ দিয়েই আর একজন চলে এল।</p>
          <p>পথ একই। সম্পর্ক একই।</p>
          <p>শুধু মানুষ ভিন্ন।</p>
          <p>২.</p>
          <p>কুসুমপুরের সোঁদা মাটিতেই অস্তিত্বহীন হবে দেহের।</p>
          <p>চেয়ে দেখার মতো চোখ থাকবে না তখন।</p>
          <p>৩.</p>
          <p>আমারও একটি নদী আছে, নাম যমুনা।</p>
          <p>জল রেখো বুকে, স্নান করতে আসব।</p>
        </div>
        """,
        book_title="নমুনা",
    )

    assert [entry["title"] for entry in toc] == ["১", "২", "৩"]
    assert [item["path"] for item in content_items] == [["১"], ["২"], ["৩"]]
    assert cleaned_main_content == ""


def test_dedupe_structured_sections_drops_source_navigation_link_lists():
    sections = dedupe_structured_sections(
        [
            {
                "title": "সূচী",
                "html": """
                <li><a href="https://www.example.com/books/alpha/">আলফা</a></li>
                <li><a href="https://www.example.com/books/beta/">বেটা</a></li>
                <li><a href="https://www.example.com/books/gamma/">গামা</a></li>
                """,
            },
            {
                "title": "ভূমিকা",
                "html": "<p>এটি বইয়ের আসল ভূমিকা।</p>",
            },
        ],
    )

    assert sections == [{"title": "ভূমিকা", "html": "<p>এটি বইয়ের আসল ভূমিকা।</p>"}]


def test_boundary_section_extraction_moves_editorial_notes_out_of_first_and_last_sections():
    toc = [
        {"title": "অধ্যায় ১", "type": "lesson", "has_content": True, "path": ["অধ্যায় ১"]},
        {"title": "অধ্যায় ২", "type": "lesson", "has_content": True, "path": ["অধ্যায় ২"]},
    ]
    content_items = [
        {
            "title": "অধ্যায় ১",
            "type": "lesson",
            "path": ["অধ্যায় ১"],
            "content": """
            <h2>অনুবাদকের কথা</h2>
            <p>এটি ভূমিকা অংশ।</p>
            <h2>অধ্যায় ১-এর শুরু</h2>
            <p>মূল অধ্যায়ের লেখা।</p>
            """,
        },
        {
            "title": "অধ্যায় ২",
            "type": "lesson",
            "path": ["অধ্যায় ২"],
            "content": """
            <p>শেষ অধ্যায়ের লেখা।</p>
            <h2>সম্পাদকের কথা</h2>
            <p>সমাপ্তি নোট।</p>
            """,
        },
    ]

    front_sections, back_sections, normalized_toc, normalized_items = (
        extract_boundary_sections_from_content_items(content_items, toc)
    )

    assert [section["title"] for section in front_sections] == ["অনুবাদকের কথা"]
    assert [section["title"] for section in back_sections] == ["সম্পাদকের কথা"]
    assert "এটি ভূমিকা অংশ।" not in normalized_items[0]["content"]
    assert "মূল অধ্যায়ের লেখা।" in normalized_items[0]["content"]
    assert "সমাপ্তি নোট।" not in normalized_items[-1]["content"]
    assert "শেষ অধ্যায়ের লেখা।" in normalized_items[-1]["content"]
    assert [entry["title"] for entry in normalized_toc] == ["অধ্যায় ১", "অধ্যায় ২"]


def test_single_page_book_structure_metadata_and_exports_are_dynamic(tmp_path):
    main_content_html = """
    <div>
      <p>প্রথম প্রকাশ: জানুয়ারি ২০২৪</p>
      <p>প্রথম সংস্করণ: বৈশাখ ১৩৮২</p>
      <p>উৎসর্গ :<br/>পাঠক, আপনাকে…</p>
      <h2>ভূমিকা</h2>
      <p>এটি বইয়ের প্রারম্ভিক বক্তব্য।</p>
      <h2>প্রথম অধ্যায়</h2>
      <p>প্রথম অধ্যায়ের মূল লেখা।</p>
      <h2>দ্বিতীয় অধ্যায়</h2>
      <p>দ্বিতীয় অধ্যায়ের মূল লেখা।</p>
      <h2>নমুনা অধ্যায়</h2>
      <p>এটি মূল অধ্যায়ের পরে থাকা প্রিভিউ অংশ।</p>
    </div>
    """

    book_info, dedication, compact_content = extract_main_content_segments(main_content_html)
    front_sections, compact_content = split_leading_front_sections(compact_content)
    toc, content_items, compact_content = infer_structured_content_from_main_content(
        compact_content,
        book_title="এক পৃষ্ঠার বই",
    )
    inferred_front_sections, back_sections, toc, content_items = (
        extract_boundary_sections_from_content_items(content_items, toc)
    )
    front_sections.extend(inferred_front_sections)
    entries = extract_front_matter_entries(book_info)

    assert {entry["key"]: entry["value"] for entry in entries} == {
        "first_published": "জানুয়ারি ২০২৪",
        "edition": "বৈশাখ ১৩৮২",
    }
    assert "পাঠক, আপনাকে" in dedication
    assert "উৎসর্গ" not in dedication
    assert [section["title"] for section in front_sections] == ["ভূমিকা"]
    assert [section["title"] for section in back_sections] == ["নমুনা অধ্যায়"]
    assert [entry["title"] for entry in toc] == ["প্রথম অধ্যায়", "দ্বিতীয় অধ্যায়"]
    assert [item["path"] for item in content_items] == [
        ["প্রথম অধ্যায়"],
        ["দ্বিতীয় অধ্যায়"],
    ]

    book_data = {
        "book_title": "এক পৃষ্ঠার বই",
        "author": "পরীক্ষা লেখক",
        "series": "",
        "book_type": "",
        "cover": "",
        "main_content": compact_content,
        "book_info": book_info,
        "dedication": dedication,
        "front_sections": front_sections,
        "back_sections": back_sections,
        "toc": toc,
        "content_items": content_items,
        "output_folder": str(tmp_path),
    }

    html_book.create_html_book(book_data)
    epub_book.create_epub(book_data)

    html_text = (tmp_path / "book.html").read_text(encoding="utf-8")
    assert html_text.index("dedication-section") < html_text.index("front-section")
    assert html_text.index("front-section") < html_text.index("toc-section")
    assert html_text.index("toc-section") < html_text.index("প্রথম অধ্যায়ের মূল লেখা")
    assert html_text.index("দ্বিতীয় অধ্যায়ের মূল লেখা") < html_text.index("back-section")
    assert "এটি মূল অধ্যায়ের পরে থাকা প্রিভিউ অংশ" in html_text

    epub_path = tmp_path / "এক পৃষ্ঠার বই.epub"
    assert epub_path.exists()
    with zipfile.ZipFile(epub_path) as archive:
        names = set(archive.namelist())
        nav_text = archive.read("EPUB/nav.xhtml").decode("utf-8")
        opf_text = archive.read("EPUB/content.opf").decode("utf-8")

    assert {
        "EPUB/dedication.xhtml",
        "EPUB/front_section_1.xhtml",
        "EPUB/toc.xhtml",
        "EPUB/lesson_1.xhtml",
        "EPUB/lesson_2.xhtml",
        "EPUB/back_section_1.xhtml",
    }.issubset(names)
    # nav.xhtml is the comprehensive EPUB-reader navigation document and
    # must list every readable page (dedication, front section, the
    # printed TOC page, every content chapter, every back section). It
    # must not link to itself (nav.xhtml). The printed toc.xhtml is
    # content-scoped and is covered by its own test below.
    assert 'href="nav.xhtml"' not in nav_text
    assert 'href="dedication.xhtml"' in nav_text
    assert 'href="front_section_1.xhtml"' in nav_text
    assert 'href="toc.xhtml"' in nav_text
    assert nav_text.index('href="lesson_1.xhtml"') < nav_text.index('href="lesson_2.xhtml"')
    assert nav_text.index('href="lesson_2.xhtml"') < nav_text.index('href="back_section_1.xhtml"')
    assert opf_text.index('href="front_section_1.xhtml"') < opf_text.index('href="toc.xhtml"')
    assert opf_text.index('href="lesson_2.xhtml"') < opf_text.index('href="back_section_1.xhtml"')


def test_epub_export_omits_blank_dedication_page(tmp_path):
    epub_book.create_epub(
        {
            "book_title": "উৎসর্গহীন বই",
            "author": "পরীক্ষা লেখক",
            "series": "",
            "book_type": "",
            "cover": "",
            "main_content": "",
            "book_info": "",
            "dedication": "",
            "front_sections": [],
            "back_sections": [],
            "toc": [{"title": "অধ্যায় ১", "path": ["অধ্যায় ১"], "has_content": True}],
            "content_items": [
                {"title": "অধ্যায় ১", "path": ["অধ্যায় ১"], "content": "<p>মূল লেখা</p>"}
            ],
            "output_folder": str(tmp_path),
        }
    )

    with zipfile.ZipFile(tmp_path / "উৎসর্গহীন বই.epub") as archive:
        names = set(archive.namelist())
        opf_text = archive.read("EPUB/content.opf").decode("utf-8")

    assert "EPUB/dedication.xhtml" not in names
    assert "dedication.xhtml" not in opf_text


def test_semantic_audit_allows_container_toc_nodes_without_direct_content_items():
    audit = audit_scraped_book(
        {
            "book_title": "অর্জুন সমগ্র ৫",
            "author": "সমরেশ মজুমদার",
            "book_info": "",
            "toc": [
                {
                    "title": "অর্জুন এবার নিউইয়র্কে",
                    "type": "lesson",
                    "has_content": False,
                    "path": ["অর্জুন এবার নিউইয়র্কে"],
                    "children": [
                        {
                            "title": "১-৩. থিয়েটার রোড",
                            "type": "topic",
                            "has_content": True,
                            "path": ["অর্জুন এবার নিউইয়র্কে", "১-৩. থিয়েটার রোড"],
                        }
                    ],
                }
            ],
            "content_items": [
                {
                    "title": "১-৩. থিয়েটার রোড",
                    "type": "topic",
                    "parent": "অর্জুন এবার নিউইয়র্কে",
                    "path": ["অর্জুন এবার নিউইয়র্কে", "১-৩. থিয়েটার রোড"],
                    "content": "<p>text</p>",
                }
            ],
        }
    )

    assert audit["duplicate_content_paths"] == []
    assert audit["duplicate_toc_paths"] == []
    assert audit["dead_toc_paths"] == []
    assert audit["missing_toc_paths_for_content"] == []
    assert not audit["has_deltas"]


def test_epub_builder_includes_visible_toc_page_before_lesson_navigation(tmp_path):
    builder = EpubBuilder(
        book_title="উদাহরণ",
        author="লেখক",
        output_folder=str(tmp_path),
    )
    builder.add_title_page()
    builder.add_info_page(scraped_book_info="<p>প্রকাশক – নমুনা</p>")
    builder.add_dedication_page(dedication_html="<p>উৎসর্গ</p>")
    builder.add_front_section_pages([{"title": "ভূমিকা", "html": "<p>শুরুর অংশ</p>"}])
    builder.add_hierarchical_toc_page(
        toc_structure=[{"title": "অধ্যায় ১", "path": ["অধ্যায় ১"], "children": []}],
        content_items=[{"title": "অধ্যায় ১", "path": ["অধ্যায় ১"], "content": "<p>মূল লেখা</p>"}],
    )
    builder.add_lesson_pages(
        [{"title": "অধ্যায় ১", "path": ["অধ্যায় ১"], "content": "<p>মূল লেখা</p>"}]
    )
    builder.build_epub("sample.epub", toc_structure=[{"title": "অধ্যায় ১", "path": ["অধ্যায় ১"], "children": []}])

    epub_path = tmp_path / "sample.epub"
    assert epub_path.exists()

    import zipfile

    import re

    with zipfile.ZipFile(epub_path) as archive:
        nav_text = archive.read("EPUB/nav.xhtml").decode("utf-8")
        toc_text = archive.read("EPUB/toc.xhtml").decode("utf-8")
        opf_text = archive.read("EPUB/content.opf").decode("utf-8")

    href_pattern = re.compile(r'href="([^"#]+)"')

    def _doc_hrefs(text):
        return [h for h in href_pattern.findall(text) if not h.startswith("http")]

    nav_hrefs = _doc_hrefs(nav_text)
    toc_hrefs = _doc_hrefs(toc_text)

    # nav.xhtml is comprehensive — it lists every readable page (title,
    # info, dedication, front sections, the printed TOC page, content
    # chapters). The printed toc.xhtml is content-scoped — it lists only
    # content chapters (and optional back sections). nav.xhtml must NOT
    # link to itself.
    assert toc_hrefs == ["lesson_1.xhtml"]
    assert "nav.xhtml" not in nav_hrefs
    for required_in_nav in (
        "title.xhtml",
        "info.xhtml",
        "dedication.xhtml",
        "front_section_1.xhtml",
        "toc.xhtml",
        "lesson_1.xhtml",
    ):
        assert required_in_nav in nav_hrefs, (required_in_nav, nav_hrefs)
    for forbidden_in_toc in (
        "cover_page.xhtml",
        "title.xhtml",
        "info.xhtml",
        "dedication.xhtml",
        "front_section_1.xhtml",
        "toc.xhtml",
        "nav.xhtml",
    ):
        assert forbidden_in_toc not in toc_hrefs, (forbidden_in_toc, toc_hrefs)
    # Printed toc.xhtml stays in the spine between front sections and content.
    assert opf_text.index('href="front_section_1.xhtml"') < opf_text.index('href="toc.xhtml"')
    assert opf_text.index('href="toc.xhtml"') < opf_text.index('href="lesson_1.xhtml"')
    assert (
        'idref="nav" linear="no"' in opf_text
        or 'linear="no" idref="nav"' in opf_text
    )


@pytest.mark.django_db
def test_upsert_source_catalog_entry_preserves_archive_display_title_when_page_metadata_overwrites():
    source_url = "https://www.example.com/books/example-book/"
    upsert_source_catalog_entry(
        metadata_entry_defaults(
            source_url=source_url,
            title="গডফাদার",
            author_line="মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম",
            raw_data={
                "display_title": "গডফাদার – মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম",
                "metadata_source": "archive_page",
            },
        )
    )

    page_metadata = parse_source_page_metadata(
        """
        <html>
          <head>
            <title>গডফাদার – মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম</title>
            <link rel="canonical" href="https://www.example.com/books/example-book/" />
          </head>
          <body>
            <div class="entry-meta entry-meta-after-content">
              <span class="entry-terms-authors"><a href="#">মারিয়ো পুজো</a></span>
            </div>
          </body>
        </html>
        """,
        source_url,
    )
    upsert_source_catalog_entry(page_metadata)

    entry = SourceCatalogEntry.objects.get(source_url=source_url)
    assert entry.raw_data["display_title"] == "গডফাদার – মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম"
    assert entry.raw_data["full_title"] == "গডফাদার – মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম"
    assert entry.raw_data["meta_author_line"] == "মারিয়ো পুজো"


def test_audit_comparison_flags_exact_role_and_toc_deltas():
    source_report = {
        "source_url": "https://www.example.com/books/example-book/",
        "contributors": [
            {"name": "মো: রিয়াজ উদ্দিন খান", "role": "translator"},
            {"name": "বুদ্ধদেব বসু", "role": "editor"},
        ],
        "toc": [
            {
                "title": "প্রথম পাঠ",
                "type": "lesson",
                "has_content": True,
                "path": ["প্রথম পাঠ"],
                "children": [
                    {
                        "title": "১. ভূমিকা",
                        "type": "topic",
                        "has_content": True,
                        "path": ["প্রথম পাঠ", "১. ভূমিকা"],
                    }
                ],
            }
        ],
        "content_items": [
            {"path": ["প্রথম পাঠ"], "content": "<p>lesson</p>"},
            {"path": ["প্রথম পাঠ", "১. ভূমিকা"], "content": "<p>topic</p>"},
        ],
        "cover_expected": True,
    }
    production_detail = {
        "contributors": [
            {"name": "মো: রিয়াজ উদ্দিন", "role": "translator"},
            {"name": "বুদ্ধদেব বসু", "role": "translator"},
        ],
        "toc": [
            {
                "title": "প্রথম পাঠ",
                "type": "lesson",
                "has_content": True,
                "path": ["প্রথম পাঠ"],
                "children": [
                    {
                        "title": "১. ভূমিকা",
                        "type": "topic",
                        "has_content": True,
                        "path": ["প্রথম পাঠ", "১. ভূমিকা"],
                    },
                    {
                        "title": "২. ফাঁকা",
                        "type": "topic",
                        "has_content": True,
                        "path": ["প্রথম পাঠ", "২. ফাঁকা"],
                    },
                ],
            }
        ],
        "raw_provenance": {
            "raw_scrape_payload": {
                "content_items": [
                    {"path": ["প্রথম পাঠ"], "content": "<p>lesson</p>"},
                ]
            }
        },
        "assets": [
            {"asset_type": "html", "status": "ready"},
        ],
    }

    comparison = compare_source_report_to_production(source_report, production_detail)

    assert comparison["has_deltas"] is True
    assert comparison["missing_contributors"] == [
        {"name": "মো: রিয়াজ উদ্দিন খান", "roles": ["translator"]}
    ]
    assert comparison["polluted_contributors"] == [
        {"name": "মো: রিয়াজ উদ্দিন", "roles": ["translator"]}
    ]
    assert comparison["role_mismatches"] == [
        {
            "name": "বুদ্ধদেব বসু",
            "source_roles": ["editor"],
            "production_roles": ["translator"],
        }
    ]
    assert comparison["missing_content_paths"] == [("প্রথম পাঠ", "১. ভূমিকা")]
    assert comparison["production_dead_toc_paths"] == [("প্রথম পাঠ", "১. ভূমিকা"), ("প্রথম পাঠ", "২. ফাঁকা")]
    assert comparison["missing_ready_assets"] == ["cover", "epub"]


def test_scrape_book_data_handles_paginated_topics_and_prunes_dead_toc_leaves(monkeypatch, tmp_path):
    root_url = "https://www.example.com/books/root-book/"
    lesson_url = "https://www.example.com/books/root-book/lesson-1/"
    topic_one_url = "https://www.example.com/books/root-book/topic-1/"
    topic_two_url = "https://www.example.com/books/root-book/topic-2/"
    topic_three_url = "https://www.example.com/books/root-book/topic-3/"
    lesson_page_url = f"{root_url}?ld-courseinfo-lesson-page=1"
    topic_page_url = f"{lesson_page_url}&ld-topic-page=42-2"

    html_map = {
        root_url: """
        <html>
          <head><title>সংগ্রহ – লেখক</title></head>
          <body>
            <div class="ld-tab-content ld-visible entry-content">
              <p>প্রারম্ভ</p>
            </div>
          </body>
        </html>
        """,
        lesson_page_url: """
        <html>
          <body>
            <div class="ld-item-lesson-item" data-ld-expand-id="42">
              <a class="ld-item-name" href="https://www.example.com/books/root-book/lesson-1/">
                <div class="ld-item-title">পাঠ 1 3 Topics</div>
              </a>
              <div id="42-container">
                <div class="ld-table-list-item">
                  <a class="ld-table-list-item-preview" href="https://www.example.com/books/root-book/topic-1/">
                    <span class="ld-topic-title">1. ভূমিকা</span>
                  </a>
                </div>
              </div>
              <a href="?ld-courseinfo-lesson-page=1&ld-topic-page=42-2">2</a>
            </div>
            <div class="ld-pagination ld-pagination-page-course_content_shortcode" data-pager-results="{&quot;total_pages&quot;: 1}"></div>
          </body>
        </html>
        """,
        topic_page_url: """
        <html>
          <body>
            <div class="ld-item-lesson-item" data-ld-expand-id="42">
              <a class="ld-item-name" href="https://www.example.com/books/root-book/lesson-1/">
                <div class="ld-item-title">পাঠ 1 3 Topics</div>
              </a>
              <div id="42-container">
                <div class="ld-table-list-item">
                  <a class="ld-table-list-item-preview" href="https://www.example.com/books/root-book/topic-2/">
                    <span class="ld-topic-title">2. আলোচনা</span>
                  </a>
                </div>
                <div class="ld-table-list-item">
                  <a class="ld-table-list-item-preview" href="https://www.example.com/books/root-book/topic-3/">
                    <span class="ld-topic-title">3. ফাঁকা</span>
                  </a>
                </div>
              </div>
            </div>
          </body>
        </html>
        """,
        lesson_url: """
        <html>
          <head><title>পাঠ 1 – লেখক</title></head>
          <body>
            <div class="ld-tab-content ld-visible entry-content">
              <p>পাঠের সারাংশ</p>
            </div>
          </body>
        </html>
        """,
        topic_one_url: """
        <html>
          <head><title>1. ভূমিকা – লেখক</title></head>
          <body>
            <div class="ld-tab-content ld-visible entry-content">
              <p>প্রথম টপিক</p>
            </div>
          </body>
        </html>
        """,
        topic_two_url: """
        <html>
          <head><title>2. আলোচনা – লেখক</title></head>
          <body>
            <div class="ld-tab-content ld-visible entry-content">
              <p>দ্বিতীয় টপিক</p>
            </div>
          </body>
        </html>
        """,
        topic_three_url: """
        <html>
          <head><title>3. ফাঁকা – লেখক</title></head>
          <body>
            <div class="ld-tab-content ld-visible entry-content"></div>
          </body>
        </html>
        """,
    }

    monkeypatch.setattr(
        legacy_scraper,
        "get_soup",
        lambda url, max_retries=3: legacy_scraper.BeautifulSoup(
            html_map[url],
            "html.parser",
        ),
    )
    monkeypatch.setattr(
        legacy_scraper,
        "create_output_folder",
        lambda _title: str(tmp_path / "output"),
    )
    monkeypatch.setattr(legacy_scraper, "download_cover_image", lambda *_args: None)
    monkeypatch.setattr(legacy_scraper.time, "sleep", lambda *_args: None)

    scraped = legacy_scraper.scrape_book_data(root_url)

    assert [entry["title"] for entry in scraped["toc"]] == ["পাঠ ১"]
    assert [child["title"] for child in scraped["toc"][0]["children"]] == [
        "১. ভূমিকা",
        "২. আলোচনা",
    ]
    assert [item["path"] for item in scraped["content_items"]] == [
        ["পাঠ ১"],
        ["পাঠ ১", "১. ভূমিকা"],
        ["পাঠ ১", "২. আলোচনা"],
    ]
    assert "পাঠের সারাংশ" in scraped["content_items"][0]["content"]
    assert "প্রথম টপিক" in scraped["content_items"][1]["content"]
    assert "দ্বিতীয় টপিক" in scraped["content_items"][2]["content"]
    assert all(child["title"] != "৩. ফাঁকা" for child in scraped["toc"][0]["children"])


def test_epub_builder_separates_front_matter_from_hierarchical_content_navigation(tmp_path):
    builder = EpubBuilder(
        book_title="উদাহরণ",
        author="লেখক",
        output_folder=str(tmp_path),
    )
    builder.add_title_page()
    builder.add_info_page(scraped_book_info="<p>তথ্য</p>")
    builder.add_lesson_pages(
        [
            {"title": "প্রথম পাঠ", "content": "<p>lesson</p>", "path": ["প্রথম পাঠ"]},
            {
                "title": "১. ভূমিকা",
                "content": "<p>topic</p>",
                "path": ["প্রথম পাঠ", "১. ভূমিকা"],
            },
        ]
    )

    navigation = builder.build_navigation_entries(
        [
            {
                "title": "প্রথম পাঠ",
                "type": "lesson",
                "has_content": True,
                "path": ["প্রথম পাঠ"],
                "children": [
                    {
                        "title": "১. ভূমিকা",
                        "type": "topic",
                        "has_content": True,
                        "path": ["প্রথম পাঠ", "১. ভূমিকা"],
                    }
                ],
            }
        ]
    )

    assert navigation[0][0].title == "প্রথম পাঠ"
    assert navigation[0][1][0].title == "১. ভূমিকা"
    # Under the new dynamic-structuring policy, nav.xhtml must never carry
    # title/info/dedication/front-section pages — only content + back matter.
    nav_targets = {entry.title for entry, _ in navigation}
    assert "শিরোনাম পৃষ্ঠা" not in nav_targets
    assert "বই বিষয়ক তথ্য" not in nav_targets
