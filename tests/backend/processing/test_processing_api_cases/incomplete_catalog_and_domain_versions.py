

def test_parse_incomplete_catalog_page_reads_entry_title_links():
    soup = processing_services.BeautifulSoup(
        """
        <html>
          <body>
            <article>
              <h2 class="entry-title">
                <a href="/books/sample-incomplete-book/">Sample Incomplete Book - Sample Author</a>
              </h2>
            </article>
            <article>
              <h2 class="entry-title">
                <a href="/books/second-incomplete-book/">Second Incomplete Book</a>
              </h2>
            </article>
          </body>
        </html>
        """,
        "html.parser",
    )

    entries = processing_services.parse_incomplete_catalog_page(soup)

    assert [entry["source_url"] for entry in entries] == [
        "https://www.example.com/books/sample-incomplete-book/",
        "https://www.example.com/books/second-incomplete-book/",
    ]
    assert entries[0]["title"] == "Sample Incomplete Book"
    assert entries[0]["author_line"] == "Sample Author"
    assert entries[0]["raw_data"]["metadata_source"] == "incomplete_archive_page"


def test_fetch_live_incomplete_page_treats_paginated_404_as_end_of_archive(monkeypatch):
    class FakeHttpError(Exception):
        def __init__(self, response):
            super().__init__("404 not found")
            self.response = response

    class FakeResponse:
        status_code = 404
        text = ""

        def raise_for_status(self):
            raise FakeHttpError(self)

    monkeypatch.setattr(
        "apps.processing.services.get_with_host_fallback",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    page = processing_services.fetch_live_incomplete_page(
        SimpleNamespace(session=object()),
        5,
    )

    assert page == []


@pytest.mark.django_db
def test_processing_domains_for_request_change_ignore_incomplete_domains_for_regular_request_updates():
    record = BookRecord.objects.create(
        id="plain-record",
        name="Plain Record",
        url="https://example.test/books/plain-record",
        category="Novel",
        writer="Writer One",
        publisher="Example Press",
    )
    domains = processing_services.processing_domains_for_request_change(
        "initial",
        "queued",
        record=record,
    )

    assert "create-requests" in domains
    assert "create-queue" in domains
    assert processing_services.PROCESSING_CARD_INCOMPLETE_OVERVIEW not in domains
    assert "incomplete-records" not in domains
    assert "incomplete-completed" not in domains


@pytest.mark.django_db
def test_processing_domains_for_request_change_include_catalog_domains_for_request_progression():
    record = BookRecord.objects.create(
        id="catalog-pipeline-record",
        name="Catalog Pipeline Record",
        url="https://example.test/books/catalog-pipeline-record",
        category="Novel",
        writer="Writer One",
        publisher="Example Press",
    )
    domains = processing_services.processing_domains_for_request_change(
        "initial",
        "queued",
        record=record,
    )

    assert "create-requests" in domains
    assert "create-queue" in domains
    assert "catalog-overview" in domains
    assert "catalog-records" in domains


@pytest.mark.django_db
def test_processing_domains_for_record_change_include_incomplete_domains_for_resolution_updates():
    record = BookRecord.objects.create(
        id="incomplete-target-record",
        name="Incomplete Target Record",
        url="https://example.test/books/incomplete-target-record",
        category="অসম্পূর্ণ বই",
        writer="Writer One",
        publisher="Example Press",
        was_incomplete=True,
        resolved_from_incomplete=False,
        will_resolve_to_category="Novel",
    )
    before_snapshot = processing_services.processing_record_snapshot(record)

    record.category = "Novel"
    record.resolved_from_incomplete = True
    record.book_creation_state = "created"
    after_snapshot = processing_services.processing_record_snapshot(record)

    domains = processing_services.processing_domains_for_record_change(
        before_snapshot,
        after_snapshot,
        current_request_state="created",
    )

    assert processing_services.PROCESSING_CARD_INCOMPLETE_OVERVIEW in domains
    assert "incomplete-records" in domains
    assert "incomplete-completed" in domains


@pytest.mark.django_db
def test_processing_domains_for_record_change_keep_completed_idle_during_incomplete_hydration():
    record = BookRecord.objects.create(
        id="hydrating-incomplete-record",
        name="Hydrating Incomplete Record",
        url="https://example.test/books/hydrating-incomplete-record",
        category="অসম্পূর্ণ বই",
        writer="Writer One",
        publisher="Example Press",
        was_incomplete=True,
        resolved_from_incomplete=False,
        will_resolve_to_category="Novel",
    )
    domains = processing_services.processing_domains_for_record_change(
        None,
        processing_services.processing_record_snapshot(record),
        current_request_state=None,
    )

    assert processing_services.PROCESSING_CARD_INCOMPLETE_OVERVIEW in domains
    assert "incomplete-records" in domains
    assert "incomplete-completed" not in domains
