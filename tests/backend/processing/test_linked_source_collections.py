from copy import deepcopy
from types import SimpleNamespace

import pytest
from apps.ingestion.pipeline.manifest_collection import CollectionOptions
from apps.ingestion.source_processing.collection_index import (
    MAX_COLLECTION_DEPTH,
    linked_book_entries,
)
from apps.ingestion.source_processing.linked_books import (
    SourceDocumentCollector,
    skip_component_cover,
)
from apps.ingestion.source_processing.verification import source_verification
from apps.processing.jobs.execution_errors import ExecutionFailure
from bs4 import BeautifulSoup

BASE = "https://source.test/books/"


def index_html(*names):
    entries = "".join(f'<li><a href="{BASE}{name}/">{name}</a></li>' for name in names)
    return f"<p>এই সংকলনের বইগুলো একসঙ্গে পড়ুন।</p><h2>সূচি</h2><ul>{entries}</ul>"


def source_page(title, body):
    return f'<h1 class="entry-title">{title}</h1><article><div class="entry-content">{body}</div></article>'


class FixtureContext:
    def __init__(self, sources):
        self.sources, self.pages, self.calls = sources, [], []
        self.session = SimpleNamespace()

    def fetch_soup(self, url, **labels):
        self.calls.append(url)
        html = self.sources[url]
        self.pages.append(
            {
                "url": url,
                "kind": labels.get("kind", "landing"),
                "status": "fetched",
                "status_code": 200,
            }
        )
        return BeautifulSoup(html, "html.parser")


@pytest.fixture
def collection(settings, tmp_path):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    sources = {
        BASE + "collection/": source_page(
            "Collected stories", index_html("first", "second")
        ),
        BASE + "first/": source_page(
            "First story", "<h2>প্রথম অধ্যায়</h2><p>প্রথম গল্পের সম্পূর্ণ লেখা।</p>"
        ),
        BASE + "second/": source_page(
            "Second story", "<h2>দ্বিতীয় অধ্যায়</h2><p>দ্বিতীয় গল্পের সম্পূর্ণ লেখা।</p>"
        ),
    }
    context = FixtureContext(sources)
    options = CollectionOptions(
        {"max_nodes": 2000},
        output_directory=tmp_path,
        cover_downloader=skip_component_cover,
    )
    return SourceDocumentCollector(context, options), sources


def test_collection_follows_its_component_books_in_source_order_and_verifies_all_text(
    collection,
):
    collector, _ = collection
    result = collector.collect(BASE + "collection/")
    evidence = source_verification(result)
    assert evidence["verified"], evidence["issues"]
    assert collector.context.calls == [
        BASE + f"{name}/" for name in ("collection", "first", "second")
    ]
    assert set(result["source_snapshot"]["fetched_urls"]) == set(
        collector.context.calls
    )
    proof = result["source_snapshot"]["linked_books"]
    assert [entry["canonical_url"] for entry in proof] == [
        BASE + "first/",
        BASE + "second/",
    ]
    assert "প্রথম গল্পের সম্পূর্ণ লেখা।" in str(result["document"]["sections"])
    assert "দ্বিতীয় গল্পের সম্পূর্ণ লেখা।" in str(result["document"]["sections"])
    assert all(
        "body-" not in " / ".join(item["path"])
        for item in result["projection"]["content_items"]
    )


def test_collection_cannot_succeed_when_a_component_is_only_a_synopsis(collection):
    collector, sources = collection
    sources[BASE + "first/"] = source_page(
        "First story", "<p>This is a novel written in 1900.</p>"
    )
    with pytest.raises(ExecutionFailure) as failure:
        collector.collect(BASE + "collection/")
    assert failure.value.failure.code == "source_description_only"
    assert BASE + "second/" not in collector.context.calls


def test_nested_collections_preserve_each_component_and_require_all_nested_proofs(
    collection,
):
    collector, sources = collection
    sources[BASE + "first/"] = source_page(
        "Nested collection", index_html("third", "fourth")
    )
    sources[BASE + "third/"] = source_page(
        "Third", "<h2>তৃতীয় অধ্যায়</h2><p>তৃতীয় বইয়ের পূর্ণ পাঠ।</p>"
    )
    sources[BASE + "fourth/"] = source_page(
        "Fourth", "<h2>চতুর্থ অধ্যায়</h2><p>চতুর্থ বইয়ের পূর্ণ পাঠ।</p>"
    )
    result = collector.collect(BASE + "collection/")
    assert source_verification(result)["verified"]
    assert "চতুর্থ বইয়ের পূর্ণ পাঠ।" in str(result["document"]["sections"])
    result["source_snapshot"]["linked_books"][0]["linked_books"].pop()
    assert not source_verification(result)["verified"]


def test_distinct_component_urls_with_the_same_title_and_text_are_not_merged(
    collection,
):
    collector, sources = collection
    sources[BASE + "collection/"] = source_page(
        "Collection",
        index_html("first", "second")
        .replace(">first<", ">Story<")
        .replace(">second<", ">Story<"),
    )
    sources[BASE + "second/"] = sources[BASE + "first/"]
    result = collector.collect(BASE + "collection/")
    assert source_verification(result)["verified"]
    assert {item["linked_book"] for item in result["projection"]["content_items"]} == {
        BASE + "first/",
        BASE + "second/",
    }


def test_collection_does_not_fetch_a_link_on_another_host(collection):
    collector, sources = collection
    sources[BASE + "collection/"] = source_page(
        "Collection",
        index_html("first", "second").replace(
            BASE + "second", "https://other.test/books/second"
        ),
    )
    with pytest.raises(ExecutionFailure) as failure:
        collector.collect(BASE + "collection/")
    assert failure.value.failure.code == "source_url_not_allowed"
    assert collector.context.calls == [BASE + "collection/"]


@pytest.mark.parametrize(
    "change", ["missing_child", "source_order", "changed_source", "missing_text"]
)
def test_retained_collection_proof_rejects_missing_reordered_or_changed_component_text(
    collection, change
):
    collector, _ = collection
    result = deepcopy(collector.collect(BASE + "collection/"))
    snapshot = result["source_snapshot"]
    if change == "missing_child":
        snapshot["linked_books"].pop()
    elif change == "source_order":
        snapshot["linked_books"].reverse()
    elif change == "changed_source":
        raw = snapshot["linked_books"][0]["raw_scrape_payload"]
        raw["main_content"] += "<p>নতুন অংশ, যা সম্মিলিত বইয়ে নেই।</p>"
    else:
        snapshot["raw_scrape_payload"]["content_items"][0]["content"] = (
            "<p>অন্য লেখা।</p>"
        )
    assert not source_verification(result)["verified"]


def test_collection_cycles_are_bounded_before_the_ancestor_is_requested_again(
    collection,
):
    collector, sources = collection
    sources[BASE + "first/"] = source_page(
        "First collection", index_html("collection", "second")
    )
    with pytest.raises(ExecutionFailure) as failure:
        collector.collect(BASE + "collection/")
    assert failure.value.failure.code == "source_layout_unknown"
    assert collector.context.calls == [BASE + "collection/", BASE + "first/"]
    with pytest.raises(ExecutionFailure):
        collector.collect(
            BASE + "collection/",
            tuple(
                f"https://source.test/{index}" for index in range(MAX_COLLECTION_DEPTH)
            ),
        )
    assert len(collector.context.calls) == 2


def test_book_references_inside_reading_text_are_not_treated_as_a_collection():
    contents = index_html("one", "two")
    html = (
        "<p>প্রথম অনুচ্ছেদ।</p><p>দ্বিতীয় অনুচ্ছেদ।</p><p>তৃতীয় অনুচ্ছেদ।</p><h2>References</h2>"
        + contents[contents.index("<ul>") :]
    )
    assert linked_book_entries(html, BASE + "story/") == []


@pytest.mark.django_db
def test_standard_worker_publishes_combined_html_epub_and_reader_files(
    source_job, monkeypatch
):
    from apps.ingestion.source_processing.documents import read_source_result
    from apps.ingestion.source_processing.transport import ControlledSourceSession
    from source_processing_fixtures import execute_source_job
    from source_transport_fixture import FixtureAdapter, fixture_request_slot

    bodies = [
        source_page("Collection", index_html("first", "second")),
        source_page("First", "<h2>প্রথম অধ্যায়</h2><p>প্রথম বইয়ের পূর্ণ পাঠ।</p>"),
        source_page("Second", "<h2>দ্বিতীয় অধ্যায়</h2><p>দ্বিতীয় বইয়ের পূর্ণ পাঠ।</p>"),
    ]
    adapter = FixtureAdapter([(200, {}, body.encode()) for body in bodies])

    def session(boundary):
        client = ControlledSourceSession(boundary, fixture_request_slot)
        client.mount("https://", adapter)
        return client

    monkeypatch.setattr(
        "apps.ingestion.source_processing.curation.ControlledSourceSession", session
    )
    execute_source_job(source_job)
    assert source_job.state == "succeeded", source_job.error_code
    source_job.book.refresh_from_db()
    assert (
        source_job.book.state == "published"
        and source_job.book.source_quality_state == "verified"
    )
    assert set(
        source_job.book.generated_assets.filter(status="ready").values_list(
            "asset_type", flat=True
        )
    ) >= {"html", "epub"}
    retained = read_source_result(source_job.pk, source_job.checkpoint["document_ref"])
    assert source_verification(retained)["verified"]
