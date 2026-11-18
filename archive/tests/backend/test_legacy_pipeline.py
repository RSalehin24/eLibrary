from pathlib import Path

from apps.ingestion.services.legacy_adapter import generate_exports, legacy_modules


def test_legacy_exports_support_structured_display_values(tmp_path):
    book_data = {
        "book_title": "রূপান্তর",
        "author": [{"name": "লেখক এক"}, {"name": "লেখক দুই"}],
        "series": [{"title": "সিরিজ এক"}],
        "book_type": [{"name": "উপন্যাস"}],
        "cover": "",
        "main_content": "<p>মূল অংশ</p>",
        "book_info": "<p>তথ্য</p>",
        "dedication": "<p>উৎসর্গ</p>",
        "toc": [{"title": "অধ্যায় ১", "type": "lesson", "has_content": True}],
        "content_items": [{"title": "অধ্যায় ১", "content": "<p>বিষয়</p>", "type": "lesson", "parent": None}],
        "output_folder": str(tmp_path),
    }

    generate_exports(book_data)

    assert (Path(tmp_path) / "book.html").exists()
    assert (Path(tmp_path) / "রূপান্তর.epub").exists()
    html = (Path(tmp_path) / "book.html").read_text(encoding="utf-8")
    assert "cover-placeholder-card" in html
    assert "ebook_preview_lock:" in html
    assert "Preview already open" in html


def test_legacy_exports_inline_existing_cover_even_if_requested_extension_is_wrong(tmp_path):
    (Path(tmp_path) / "book_cover.jpg").write_bytes(b"fake-jpg")
    book_data = {
        "book_title": "রূপান্তর",
        "author": "লেখক এক",
        "series": "",
        "book_type": "",
        "cover": "book_cover.jog",
        "main_content": "<p>মূল অংশ</p>",
        "book_info": "",
        "dedication": "",
        "toc": [{"title": "অধ্যায় ১", "type": "lesson", "has_content": True}],
        "content_items": [{"title": "অধ্যায় ১", "content": "<p>বিষয়</p>", "type": "lesson", "parent": None}],
        "output_folder": str(tmp_path),
    }

    generate_exports(book_data)

    html = (Path(tmp_path) / "book.html").read_text(encoding="utf-8")
    assert "data:image/jpeg;base64," in html
    assert "book_cover.jog" not in html


def test_legacy_exports_dedication_section_uses_standard_heading_and_clean_content(tmp_path):
    book_data = {
        "book_title": "রূপান্তর",
        "author": "লেখক এক",
        "series": "",
        "book_type": "",
        "cover": "",
        "main_content": "<p>মূল অংশ</p>",
        "book_info": "",
        "dedication": "<p>Dedication</p><p>For readers.</p>",
        "toc": [{"title": "অধ্যায় ১", "type": "lesson", "has_content": True}],
        "content_items": [{"title": "অধ্যায় ১", "content": "<p>বিষয়</p>", "type": "lesson", "parent": None}],
        "output_folder": str(tmp_path),
    }

    generate_exports(book_data)

    html = (Path(tmp_path) / "book.html").read_text(encoding="utf-8")
    assert "<h2 class='dedication-title'>Dedication</h2>" in html
    assert "<p>For readers.</p>" in html
    assert "<p>Dedication</p>" not in html


def test_legacy_scraper_extracts_leading_front_matter_without_dedication():
    scraper, _, _ = legacy_modules()
    main_content = """
    <div>
      <p><strong>অনুবাদ</strong>: অনুবাদক এক</p>
      <p><strong>প্রথম প্রকাশ</strong>: জানুয়ারি ২০০১</p>
      <p>এটাই মূল কনটেন্ট।</p>
    </div>
    """

    book_info, dedication, cleaned_content = scraper.extract_dedication(main_content)

    assert "অনুবাদক এক" in book_info
    assert "জানুয়ারি ২০০১" in book_info
    assert dedication == ""
    assert "অনুবাদক এক" not in cleaned_content
    assert "জানুয়ারি ২০০১" not in cleaned_content
    assert "এটাই মূল কনটেন্ট।" in cleaned_content


def test_legacy_scraper_extracts_title_prefixed_translator_and_publication_from_main_content():
    scraper, _, _ = legacy_modules()
    main_content = """
    <div>
      <h2 class="wp-block-heading">ম্যালিস – কিয়েগো হিগাশিনো</h2>
      <p><strong>ম্যালিস – কিয়েগো হিগাশিনো</strong><br/>অনুবাদ: সালমান হক, ইশরাক অর্ণব</p>
      <p>প্রথম প্রকাশ: মার্চ ২০২৩</p>
      <p><strong>ভূমিকা</strong></p>
      <p>এটাই মূল কনটেন্ট।</p>
    </div>
    """

    book_info, dedication, cleaned_content = scraper.extract_dedication(main_content)

    assert "অনুবাদ: সালমান হক, ইশরাক অর্ণব" in book_info
    assert "প্রথম প্রকাশ: মার্চ ২০২৩" in book_info
    assert dedication == ""
    assert "অনুবাদ: সালমান হক, ইশরাক অর্ণব" not in cleaned_content
    assert "প্রথম প্রকাশ: মার্চ ২০২৩" not in cleaned_content
    assert "এটাই মূল কনটেন্ট।" in cleaned_content


def test_legacy_scraper_dedication_heading_does_not_pollute_extracted_dedication():
        scraper, _, _ = legacy_modules()
        main_content = """
        <div>
            <h2>উৎসর্গ</h2>
            <p>স্ট্যানলির স্মৃতির প্রতি</p>
            <p>তোমাকে শ্রদ্ধা।</p>
            <h2>প্রারম্ভ কথন</h2>
            <p>এটাই মূল কনটেন্ট।</p>
        </div>
        """

        _, dedication, cleaned_content = scraper.extract_dedication(main_content)

        assert "উৎসর্গ" not in dedication
        assert "স্ট্যানলির স্মৃতির প্রতি" in dedication
        assert "এটাই মূল কনটেন্ট।" in cleaned_content


def test_legacy_scraper_does_not_treat_translator_bio_as_book_info():
        scraper, _, _ = legacy_modules()
        main_content = """
        <div>
            <p>পঁয়ত্রিশটি ভাষায় অনূদিত মহাকাশ উপন্যাস ওডিসি সিরিজ</p>
            <p>২০০১: আ স্পেস ওডিসি</p>
            <p>আর্থার সি ক্লাক</p>
            <p>অনুবাদ : মাকসুদুজ্জামান খান</p>
            <p>অনুবাদক মাকসুদুজ্জামান খান বায়োটেকনোলজি এন্ড জেনেটিক ইঞ্জিনিয়ারিং এ পড়ালেখা করছেন। তিনি আর্থার সি ক্লার্ক ও আইজাক আসিমভের বেশ কিছু লেখা ভাষান্তর করেছেন।</p>
            <p>এটাই মূল কনটেন্ট।</p>
        </div>
        """

        book_info, dedication, cleaned_content = scraper.extract_dedication(main_content)

        assert "অনুবাদ : মাকসুদুজ্জামান খান" in book_info
        assert "অনুবাদক মাকসুদুজ্জামান খান বায়োটেকনোলজি" not in book_info
        assert dedication == ""
        assert "অনুবাদক মাকসুদুজ্জামান খান বায়োটেকনোলজি" in cleaned_content


def test_legacy_scraper_stops_dedication_before_letter_excerpt():
        scraper, _, _ = legacy_modules()
        main_content = """
        <div>
            <h2>উৎসর্গ</h2>
            <p>সাত বছরের বন্ধুত্ব শেষে নাফিস আমাকে বলেছিল।</p>
            <p>আহমেদ নাফিস শাহরিয়ারকে।</p>
            <p>যে অনুষ্ঠানে আমার উপস্থিতির সময় তার পাঠানো চিঠিতে</p>
            <p>২২ আগস্ট, ১৯৯৪</p>
            <p>প্রিয় আর্থার,</p>
            <p>সরি, ফিল্মের কাজের চাপ আমাকে আপনার এই বিশেষ সম্মান পাওয়া দেখা থেকে বঞ্চিত করল।</p>
        </div>
        """

        _, dedication, cleaned_content = scraper.extract_dedication(main_content)

        assert "সাত বছরের বন্ধুত্ব শেষে নাফিস" in dedication
        assert "আহমেদ নাফিস শাহরিয়ারকে" in dedication
        assert "যে অনুষ্ঠানে আমার উপস্থিতির সময় তার পাঠানো চিঠিতে" not in dedication
        assert "প্রিয় আর্থার" not in dedication
        assert "প্রিয় আর্থার" in cleaned_content


def test_legacy_scraper_does_not_match_anubad_alias_inside_anubadok_word():
        scraper, _, _ = legacy_modules()
        main_content = """
        <div>
            <p>অনুবাদক মাকসুদুজ্জামান খান বায়োটেকনোলজি এন্ড জেনেটিক ইঞ্জিনিয়ারিং এ পড়ালেখা করছেন।</p>
            <p>তিনি আর্থার সি ক্লার্ক ও আইজাক আসিমভের বেশ কিছু লেখা ভাষান্তর করেছেন।</p>
            <p>এটাই মূল কনটেন্ট।</p>
        </div>
        """

        book_info, dedication, cleaned_content = scraper.extract_dedication(main_content)

        assert book_info == ""
        assert dedication == ""
        assert "অনুবাদক মাকসুদুজ্জামান খান" in cleaned_content


def test_legacy_scraper_uses_dot_separator_to_end_dedication_section():
        scraper, _, _ = legacy_modules()
        main_content = """
        <div>
            <h2>উৎসর্গ</h2>
            <p>আহমেদ নাফিস শাহরিয়ারকে</p>
            <p>.</p>
            <p>প্রিয় আর্থার,</p>
            <p>এই অংশ dedication-এ যাবে না।</p>
            <p>এটাই মূল কনটেন্ট।</p>
        </div>
        """

        _, dedication, cleaned_content = scraper.extract_dedication(main_content)

        assert "আহমেদ নাফিস শাহরিয়ারকে" in dedication
        assert "প্রিয় আর্থার" not in dedication
        assert "এই অংশ dedication-এ যাবে না" not in dedication
        assert "প্রিয় আর্থার" in cleaned_content


def test_legacy_scraper_extracts_inline_dedication_inside_large_preface_block():
        scraper, _, _ = legacy_modules()
        main_content = """
        <div>
            <p>
                ভূমিকা
                এর আগে আমি কিয়েগো হিগাশিনোর ডিটেক্টিভ গ্যালিলিও সিরিজের দুটো বই অনুবাদ করেছি।
                সবাই ভালো থাকবেন।
                সালমান হক
                মার্চ, ঢাকা
                উৎসর্গ :
                পাঠক, আপনাকে…
            </p>
            <p>সূচিপত্র</p>
            <p>অধ্যায় ১</p>
        </div>
        """

        _, dedication, cleaned_content = scraper.extract_dedication(main_content)

        assert "পাঠক, আপনাকে" in dedication
        assert "উৎসর্গ" not in dedication
        assert "ভূমিকা" in cleaned_content
        assert "পাঠক, আপনাকে" not in cleaned_content
