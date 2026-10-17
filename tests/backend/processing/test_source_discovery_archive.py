import pytest
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.services.resolution import TitleResolver
from apps.ingestion.source_discovery.parser import discovery_page
from apps.processing.jobs.execution_errors import ExecutionFailure
from bs4 import BeautifulSoup
from test_source_discovery import controlled_replies, discovery_job, execute

__all__ = ["discovery_job"]

pytestmark = pytest.mark.django_db
CATALOG_URL = "https://source.test/books/"


def facet_archive(number=None):
    result = (
        ""
        if number is None
        else f"""
      <div class="fwpl-result"><div class="fwpl-row"><div class="fwpl-col">
        <div class="fwpl-item image"><a href="/books/story-{number}/"><img alt="cover"></a></div>
        <div class="fwpl-item changed-title-class"><a href="/books/story-{number}/">গল্প {number} - লেখক এক</a></div>
      </div></div></div>"""
    )
    return f'<div class="facetwp-template" data-name="books">{result}</div><div class="facetwp-type-pager"></div>'.encode()


def test_discovery_extracts_facet_titles_and_follows_server_side_pagination(
    discovery_job, monkeypatch
):
    adapter = controlled_replies(
        monkeypatch,
        [
            (200, {}, facet_archive(1)),
            (200, {}, facet_archive(2)),
        ],
    )
    execute(discovery_job)
    assert discovery_job.state == "succeeded"
    assert list(
        SourceCatalogEntry.objects.order_by("title").values_list("title", "author_line")
    ) == [
        ("গল্প 1", "লেখক এক"),
        ("গল্প 2", "লেখক এক"),
    ]
    assert adapter.calls[1][0].url == CATALOG_URL + "?_paged=2"
    assert discovery_job.checkpoint["discovered_entries"] == 2
    assert discovery_job.checkpoint["more_pages_available"]


def test_known_empty_facet_page_terminates_after_collected_books(
    discovery_job, monkeypatch
):
    controlled_replies(
        monkeypatch, [(200, {}, facet_archive(1)), (200, {}, facet_archive())]
    )
    execute(discovery_job)
    assert discovery_job.state == "succeeded"
    assert discovery_job.checkpoint["discovered_entries"] == 1
    assert discovery_job.checkpoint["discovered_pages"] == 2
    assert not discovery_job.checkpoint["more_pages_available"]


@pytest.mark.parametrize(
    "specimen",
    [
        (facet_archive(), "source_catalog_empty"),
        (b"<html><h1>Please wait</h1></html>", "source_catalog_layout_unrecognized"),
        (
            b'<div class="facetwp-template"><div class="changed-result"><a href="/books/a/">A book</a></div></div>',
            "source_catalog_layout_unrecognized",
        ),
        (
            b'<div class="facetwp-template"><div class="fwpl-result"><a href="/books/a/"><img></a></div></div>',
            "source_discovery_metadata_invalid",
        ),
    ],
)
def test_empty_or_unrecognized_initial_page_never_reports_success(
    discovery_job, monkeypatch, specimen
):
    body, code = specimen
    controlled_replies(monkeypatch, [(200, {}, body)])
    execute(discovery_job)
    assert discovery_job.state == "failed" and discovery_job.error_code == code
    assert not SourceCatalogEntry.objects.exists()
    assert not discovery_job.checkpoint.get("discovery_complete")


def test_pagination_that_repeats_results_fails_without_counting_duplicates(
    discovery_job, monkeypatch
):
    controlled_replies(
        monkeypatch, [(200, {}, facet_archive(1)), (200, {}, facet_archive(1))]
    )
    execute(discovery_job)
    assert discovery_job.state == "failed"
    assert discovery_job.error_code == "source_catalog_pagination_stalled"
    assert discovery_job.checkpoint["discovered_entries"] == 1
    assert SourceCatalogEntry.objects.count() == 1


@pytest.mark.parametrize(
    "body",
    [b"<h1>Unavailable</h1>", b'<div class="facetwp-template">Unavailable</div>'],
)
def test_unrecognized_later_page_keeps_prior_progress_and_reports_failure(
    discovery_job, monkeypatch, body
):
    controlled_replies(monkeypatch, [(200, {}, facet_archive(1)), (200, {}, body)])
    execute(discovery_job)
    assert discovery_job.state == "failed"
    assert discovery_job.error_code == "source_catalog_layout_unrecognized"
    assert discovery_job.checkpoint["discovered_entries"] == 1
    assert SourceCatalogEntry.objects.count() == 1


def test_facet_pagination_preserves_filters_and_replaces_page_parameter(settings):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    soup = BeautifulSoup(facet_archive(1), "html.parser")
    _, next_url = discovery_page(soup, CATALOG_URL + "?_a_z=A&_paged=3&filter=x")
    assert next_url == CATALOG_URL + "?_a_z=A&filter=x&_paged=4"


@pytest.mark.parametrize(
    "query", ["_paged=bad", "_paged=0", "_paged=2&_paged=3", "_paged=²"]
)
def test_invalid_facet_pagination_is_rejected(settings, query):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    with pytest.raises(ExecutionFailure) as error:
        discovery_page(
            BeautifulSoup(facet_archive(1), "html.parser"), CATALOG_URL + "?" + query
        )
    assert error.value.failure.code == "source_catalog_pagination_invalid"


def test_original_resolver_reuses_text_anchor_extraction(settings):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    entries = TitleResolver().parse_catalog_page(
        BeautifulSoup(facet_archive(1), "html.parser")
    )
    assert len(entries) == 1 and entries[0]["title"] == "গল্প 1"


def test_fetch_all_scans_past_page_limit_until_known_empty_archive(
    discovery_job, monkeypatch
):
    from uuid import uuid4

    from apps.ingestion.source_discovery.commands import request_source_discovery
    from apps.processing.job_models import BackgroundJob

    BackgroundJob.objects.filter(pk=discovery_job.pk).update(state="cancelled")
    command = {
        "operation_id": uuid4(),
        "configuration_revision": discovery_job.input["command"][
            "configuration_revision"
        ],
        "max_pages": 1,
        "fetch_all": True,
    }
    job = request_source_discovery(discovery_job.requested_by, command)
    adapter = controlled_replies(
        monkeypatch,
        [
            (200, {}, facet_archive(1)),
            (200, {}, facet_archive(2)),
            (200, {}, facet_archive()),
        ],
    )
    execute(job)
    assert job.state == "succeeded" and len(adapter.calls) == 3
    assert (
        job.checkpoint["discovered_entries"] == 2
        and not job.checkpoint["more_pages_available"]
    )
    assert job.input["command"]["fetch_all"] and job.input["command"]["max_pages"] > 200


def test_fetch_all_never_claims_completion_at_a_safety_limit(
    discovery_job, monkeypatch
):
    discovery_job.input["command"]["fetch_all"] = True
    discovery_job.save()
    controlled_replies(
        monkeypatch, [(200, {}, facet_archive(1)), (200, {}, facet_archive(2))]
    )
    execute(discovery_job)
    assert (
        discovery_job.state == "failed"
        and discovery_job.error_code == "source_catalog_scan_limit"
    )
    assert SourceCatalogEntry.objects.count() == 1
