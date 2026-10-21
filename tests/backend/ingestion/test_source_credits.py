from apps.ingestion.services.normalization import normalize_scraped_book
from apps.ingestion.services.source_credits import curate_explicit_credits


def pairs(payload):
    return {
        (entry["name"], entry["role"])
        for entry in normalize_scraped_book(payload)["contributors"]
    }


def test_explicit_translator_credit_overrides_verified_taxonomy_spelling():
    payload = {"author": "জেমস রোলিন্স, সাঈম শামস", "book_info": "<p>অনুবাদক: সাঈম শামস্</p>"}
    assert pairs(payload) == {("জেমস রোলিন্স", "author"), ("সাঈম শামস্", "translator")}
    assert pairs({"author": "সাঈম শামস"}) == {("সাঈম শামস", "author")}


def test_verified_cover_credit_is_cleaned_without_losing_raw_evidence():
    raw = "বিদেশি ছবি অবলম্বনে কোলায বনবীর আহমেদ বিতর"
    entry = {"name": raw, "role": "cover_artist", "raw_value": raw}
    assert curate_explicit_credits([entry]) == [{**entry, "name": "বনবীর আহমেদ"}]
    assert entry["name"] == raw


def test_prose_is_not_a_publisher_and_real_publisher_names_are_retained():
    entries = [
        {"name": name, "role": "publisher"}
        for name in [
            "তাড়া দিচ্ছেন",
            "সূচীপত্র",
            "সাঈদ বারী",
            "ফরিদ আহমেদ",
            "এর জনাব ফরিদ আহমেদ",
        ]
    ]
    result = curate_explicit_credits(entries)
    assert [entry["name"] for entry in result] == [
        "সূচীপত্র",
        "সাঈদ বারী",
        "ফরিদ আহমেদ",
        "ফরিদ আহমেদ",
    ]
    unknown = {"name": "এর জনাব অন্য নাম", "role": "publisher"}
    assert curate_explicit_credits([unknown]) == [unknown]


def test_similar_names_are_never_fuzzily_merged_or_reclassified():
    payload = {
        "author": "ফরিদ আহমেদ, ফরীদ আহমেদ",
        "book_info": "<p>প্রচ্ছদ: মানস চক্রবর্তী</p>",
    }
    assert pairs(payload) == {
        ("ফরিদ আহমেদ", "author"),
        ("ফরীদ আহমেদ", "author"),
        ("মানস চক্রবর্তী", "cover_artist"),
    }
