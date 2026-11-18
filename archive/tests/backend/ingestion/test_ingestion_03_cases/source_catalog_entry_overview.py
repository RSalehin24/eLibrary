

@pytest.mark.django_db
def test_source_catalog_entries_overview_returns_summary_and_reviewable_rows_only(client):
    admin = User.objects.create_superuser(email="catalog-overview@example.com", password="strong-password-123")
    client.force_login(admin)

    failed_source_url = "https://www.example.com/books/failed-overview/"
    failed_submission = BookSubmission.objects.create(
        submitter=admin,
        input_type="url",
        original_input=failed_source_url,
        normalized_input="failed overview",
        resolved_url=failed_source_url,
        origin=SubmissionOrigin.CURATION,
        status=SubmissionStatus.FAILED,
        error_message="seeded failure",
    )
    ProcessingJob.objects.create(
        submission=failed_submission,
        status=JobStatus.FAILED,
        last_error="seeded failure",
    )
    SourceCatalogEntry.objects.create(
        source_url=failed_source_url,
        title="Failed Overview",
        author_line="Writer",
        normalized_title="failed overview",
        normalized_display="failed overview writer",
    )

    ready_book = Book.objects.create(title="Ready Overview", state=LifecycleState.READY)
    ready_source_url = "https://www.example.com/books/ready-overview/"
    BookSource.objects.create(
        book=ready_book,
        source_url=ready_source_url,
        normalized_source_url=ready_source_url,
    )
    GeneratedAsset.objects.create(book=ready_book, asset_type=GeneratedAssetType.HTML, status=GeneratedAssetStatus.READY)
    GeneratedAsset.objects.create(book=ready_book, asset_type=GeneratedAssetType.EPUB, status=GeneratedAssetStatus.READY)
    SourceCatalogEntry.objects.create(
        source_url=ready_source_url,
        title="Ready Overview",
        author_line="Writer",
        normalized_title="ready overview",
        normalized_display="ready overview writer",
    )

    response = client.get("/api/ingestion/catalog/entries/?view=overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 2
    assert payload["summary"]["failed"] == 1
    assert payload["summary"]["ready"] == 1
    assert [entry["title"] for entry in payload["entries"]] == ["Failed Overview"]
