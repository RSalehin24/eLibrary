from unittest.mock import Mock
from uuid import uuid4

import pytest
from apps.ingestion.pipeline.source_html import (
    preserve_single_flow_body,
    repair_source_html,
)
from apps.ingestion.source_processing.documents import (
    read_source_result,
    write_source_result,
)
from apps.ingestion.source_processing.storage import read_artifact, write_artifact
from apps.ingestion.source_processing.transport import ControlledSourceSession
from apps.processing.jobs.execution_errors import ExecutionFailure
from source_transport_fixture import FixtureAdapter, fixture_request_slot


def test_public_contents_pager_nonce_is_allowed_only_for_the_expected_read_action(
    settings,
):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    session = ControlledSourceSession(Mock(), fixture_request_slot)
    adapter = FixtureAdapter([(200, {}, b'{"data":{"markup":"Contents"}}')])
    session.mount("https://", adapter)
    response = session.get(
        "https://source.test/wp-admin/admin-ajax.php",
        params={
            "action": "ld30_ajax_pager",
            "context": "course_content_shortcode",
            "pager_nonce": "public-page-nonce",
            "ld-courseinfo-lesson-page": 2,
        },
    )
    assert response.status_code == 200 and len(adapter.calls) == 1
    for query in [
        "action=write&context=course_content_shortcode&pager_nonce=secret",
        "action=ld30_ajax_pager&context=other&pager_nonce=secret",
        "action=ld30_ajax_pager&context=course_content_shortcode&token=secret",
        "action=ld30_ajax_pager&context=course_content_shortcode&pager_nonce=public&auth=secret",
    ]:
        with pytest.raises(ExecutionFailure):
            session.get(f"https://source.test/wp-admin/admin-ajax.php?{query}")
    with pytest.raises(ExecutionFailure):
        session.get("https://source.test/books/example/?pager_nonce=secret")
    assert len(adapter.calls) == 1


def test_source_numeric_entities_are_repaired_before_html_and_xml_exports():
    from bs4 import BeautifulSoup

    value = "<p>গুঁড়িত\x19#2503; ম\x02#2507;শি \x01শব্দ</p>"
    repaired = repair_source_html(value)
    assert BeautifulSoup(repaired, "html.parser").get_text() == "গুঁড়িতে মোশি শব্দ"
    assert (
        repair_source_html("<p>বাংলা &amp; English\nলেখা</p>")
        == "<p>বাংলা &amp; English\nলেখা</p>"
    )


def test_single_flow_book_is_preserved_when_an_introductory_heading_consumes_the_body():
    sections = {
        "toc": [],
        "content_items": [],
        "main_content": "",
        "front_sections": [{"title": "ভূমিকা", "html": "<p>উপন্যাসের সম্পূর্ণ লেখা।</p>"}],
        "back_sections": [],
        "book_info": "<p>লেখক: একজন লেখক</p>",
    }
    restored = preserve_single_flow_body(sections)
    assert "উপন্যাসের সম্পূর্ণ লেখা।" in restored["main_content"]
    assert (
        restored["front_sections"] == []
        and restored["book_info"] == sections["book_info"]
    )
    structured = {**sections, "toc": [{"title": "অধ্যায়"}]}
    assert preserve_single_flow_body(structured) == structured
    metadata_only = {**sections, "front_sections": []}
    assert preserve_single_flow_body(metadata_only)["main_content"] == ""


def test_partitioned_book_checkpoint_keeps_each_artifact_bounded(
    tmp_path, settings, monkeypatch
):
    settings.RUNTIME_STORAGE_DIR = tmp_path
    monkeypatch.setattr(
        "apps.ingestion.source_processing.storage.MAX_DOCUMENT_BYTES", 300
    )
    identifier = uuid4()
    result = {
        "document": {"html": "a" * 180},
        "source_snapshot": {"html": "b" * 180},
        "projection": {"html": "c" * 180},
        "status": "validated",
        "validation": {},
    }
    with pytest.raises(ExecutionFailure):
        write_artifact(identifier, result)
    reference = write_source_result(identifier, result)
    assert read_source_result(identifier, reference) == result
    assert (
        read_artifact(identifier, reference)["artifact_format"]
        == "source-result-parts-v1"
    )


def test_partitioned_checkpoints_preserve_legacy_documents_and_reject_invalid_parts(
    tmp_path, settings
):
    settings.RUNTIME_STORAGE_DIR = tmp_path
    identifier = uuid4()
    legacy = {"document": {}, "status": "validated"}
    assert read_source_result(identifier, write_artifact(identifier, legacy)) == legacy
    reference = write_artifact(
        identifier, {"artifact_format": "source-result-parts-v1", "parts": {}}
    )
    with pytest.raises(ExecutionFailure):
        read_source_result(identifier, reference)
