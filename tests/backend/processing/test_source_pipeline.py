import pytest
from apps.catalog.models import Book, UserBook
from apps.ingestion.source_processing.transport import ControlledSourceSession
from source_processing_fixtures import TITLE, execute_source_job
from source_transport_fixture import FixtureAdapter, fixture_request_slot

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "cover",
    [
        "",
        '<figure class="entry-image-link"><img src="https://images.source.test/cover.jpg"></figure>',
    ],
)
def test_network_page_collection_curation_persistence_and_export_are_one_workflow(
    source_job, monkeypatch, cover
):
    html = f'<html lang="bn"><head><title>{TITLE}</title></head><body><h1 class="entry-title">{TITLE}</h1>{cover}<article><div class="entry-content"><h2>মূল লেখা</h2><p>পরীক্ষার বাংলা গল্প। পাঠকের জন্য সম্পূর্ণ মূল পাঠ।</p></div></article></body></html>'
    adapter = FixtureAdapter(
        [(200, {"Content-Type": "text/html; charset=utf-8"}, html.encode())]
    )

    def fixture_session(boundary):
        session = ControlledSourceSession(boundary, fixture_request_slot)
        session.mount("https://", adapter)
        return session

    monkeypatch.setattr(
        "apps.ingestion.source_processing.curation.ControlledSourceSession",
        fixture_session,
    )
    execute_source_job(source_job)
    assert (
        source_job.state == "succeeded" and source_job.checkpoint["pages_fetched"] == 1
    )
    assert len(adapter.calls) == 1 and adapter.calls[0][1]["verify"] is True
    book = Book.objects.get(pk=source_job.book_id)
    assert book.title == TITLE and "পরীক্ষার বাংলা গল্প" in book.main_content_html
    assert book.state == "published" and source_job.asset.file.size > 0
    assert not UserBook.objects.exists()
