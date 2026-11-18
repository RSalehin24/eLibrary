def handle(self, *args, **options):
    if not settings.SUPER_ADMIN_EMAIL or not settings.SUPER_ADMIN_PASSWORD:
        raise CommandError(
            "SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD must be set before seeding E2E data."
        )

    from apps.processing.models import (
        BookCreationRequest,
        BookCreationRequestState,
        BookRecord,
    )
    from apps.processing.services import (
        rebuild_processing_ui_state,
        reset_processing_data,
        sync_record_state,
    )

    call_command("seed_superadmin")
    admin = User.objects.filter(email=settings.SUPER_ADMIN_EMAIL).first()
    if admin is None:
        raise CommandError("Could not resolve the configured super admin account.")

    # Reset throttle/session cache so repeated live-browser runs start cleanly.
    cache.clear()
    reset_processing_data(revoke_tasks=True, purge_queue=True)

    with transaction.atomic():
        self.cleanup_existing_records()
        access_user = self.create_access_user(admin)
        books = self.create_books()
        self.create_access_grants(admin, access_user)
        self.create_reader_state(admin, books["detail"])
        self.create_submissions(admin, books)
        self.create_catalog_state(admin)
        self.create_processing_state(
            BookRecord=BookRecord,
            BookCreationRequest=BookCreationRequest,
            BookCreationRequestState=BookCreationRequestState,
            sync_record_state=sync_record_state,
        )

    rebuild_processing_ui_state()

    self.stdout.write(
        self.style.SUCCESS(
            "Seeded live E2E data for access, catalog, book detail, and processing flows."
        )
    )
def cleanup_existing_records(self):
    e2e_book_filter = Q(book__title__startswith=E2E_TITLE_PREFIX) | Q(
        book__source_urls__normalized_source_url__startswith=E2E_SOURCE_PREFIX
    )
    for asset in (
        GeneratedAsset.objects.select_related("book")
        .filter(e2e_book_filter)
        .distinct()
    ):
        if asset.file and asset.file.name:
            asset.file.delete(save=False)

    Book.objects.filter(
        Q(title__startswith=E2E_TITLE_PREFIX)
        | Q(source_urls__normalized_source_url__startswith=E2E_SOURCE_PREFIX)
    ).distinct().delete()
    BookSource.objects.filter(normalized_source_url__startswith=E2E_SOURCE_PREFIX).delete()
    SourceCatalogEntry.objects.filter(source_url__startswith=E2E_SOURCE_PREFIX).delete()
    CatalogCurationRun.objects.all().delete()
    BookSubmission.objects.filter(
        Q(original_input__startswith=E2E_TITLE_PREFIX)
        | Q(original_input__startswith=E2E_SOURCE_PREFIX)
        | Q(resolved_url__startswith=E2E_SOURCE_PREFIX)
    ).delete()
    PermissionGrant.objects.filter(user__email__endswith=E2E_EMAIL_DOMAIN).delete()
    User.objects.filter(email__endswith=E2E_EMAIL_DOMAIN).delete()
def create_access_user(self, admin: User) -> User:
    access_user = User.objects.create_user(
        email=ACCESS_USER_EMAIL,
        password=ACCESS_USER_PASSWORD,
        full_name="E2E Access Manager",
        is_active=True,
    )
    PermissionGrant.objects.create(
        user=access_user,
        scope=PermissionScope.METADATA_EDIT,
        granted_by=admin,
    )
    return access_user
def create_books(self) -> dict[str, Book]:
    books: dict[str, Book] = {}
    for key, definition in BOOK_DEFINITIONS.items():
        book = Book.objects.create(
            title=definition.title,
            summary=f"{definition.title} summary for live browser coverage.",
            state=LifecycleState.READY,
            review_state=ReviewState.APPROVED,
            record_type=BookRecordType.DIGITAL,
            source_site="e2e.local",
            raw_scraped_metadata={"seed": "e2e"},
            raw_scrape_payload={"seed": "e2e"},
            main_content_html=f"<h1>{definition.title}</h1><p>Seeded content.</p>",
            book_info_html="<p>Book ID: seeded-e2e</p>",
            toc=[{"label": "Chapter 1", "href": "#chapter-1"}],
            content_items=[{"title": "Chapter 1", "slug": "chapter-1"}],
        )
        replace_book_relations(
            book,
            contributors=[{"name": DEFAULT_WRITER, "role": ContributorRole.AUTHOR}],
            series_names=list(definition.series),
            category_names=list(definition.categories),
        )
        BookSource.objects.create(
            book=book,
            source_url=definition.source_url,
            normalized_source_url=definition.source_url,
            source_type="e2e_source",
            source_title=definition.title,
            is_primary=True,
        )
        if definition.with_assets:
            self.attach_asset(
                book,
                GeneratedAssetType.HTML,
                "book.html",
                "text/html",
                f"<html><body><h1>{definition.title}</h1><p>HTML preview</p></body></html>",
            )
            self.attach_asset(
                book,
                GeneratedAssetType.EPUB,
                "book.epub",
                "application/epub+zip",
                build_simple_epub(definition.title),
            )
        books[key] = book
    return books
def attach_asset(
    self,
    book: Book,
    asset_type: str,
    filename: str,
    content_type: str,
    content: bytes | str,
):
    payload = content.encode("utf-8") if isinstance(content, str) else content
    asset = GeneratedAsset.objects.create(
        book=book,
        asset_type=asset_type,
        status=GeneratedAssetStatus.READY,
        content_type=content_type,
        file_size=len(payload),
        is_protected=True,
    )
    asset.file.save(filename, ContentFile(payload), save=False)
    asset.storage_path = asset.file.name
    asset.save()
def create_access_grants(self, admin: User, access_user: User):
    access_book = Book.objects.get(title=BOOK_DEFINITIONS["access"].title)
    PermissionGrant.objects.create(
        user=access_user,
        book=access_book,
        scope=PermissionScope.METADATA_EDIT,
        granted_by=admin,
    )
def create_reader_state(self, admin: User, detail_book: Book):
    ReadingSession.objects.create(
        user=admin,
        book=detail_book,
        last_location="text/chapter-1.xhtml",
        progress_percent=42.0,
    )
    Bookmark.objects.create(
        user=admin,
        book=detail_book,
        location="text/chapter-1.xhtml",
        label="Seeded Bookmark",
        note="Remove me during the live test.",
    )
def create_submission_record(
    self,
    *,
    submitter: User,
    title: str,
    origin: str,
    status: str,
    review_state: str = ReviewState.PENDING,
    linked_book: Book | None = None,
    input_type: str = SubmissionInputType.TITLE,
    resolved_url: str | None = None,
    resolution_status: str = ResolutionStatus.RESOLVED,
    resolution_confidence: float = 0.95,
    error_message: str = "",
) -> BookSubmission:
    return BookSubmission.objects.create(
        submitter=submitter,
        input_type=input_type,
        origin=origin,
        original_input=title,
        normalized_input=normalize_catalog_text(title),
        resolved_url=resolved_url if resolved_url is not None else seed_source_url(title),
        resolution_status=resolution_status,
        resolution_confidence=resolution_confidence,
        status=status,
        review_state=review_state,
        linked_book=linked_book,
        error_message=error_message,
    )
def create_processing_job_record(
    self,
    *,
    submission: BookSubmission,
    book: Book | None = None,
    status: str,
    job_type: str = JobType.INGESTION,
    queue_name: str = "",
    task_id: str = "",
    last_error: str = "",
    cancel_requested: bool = False,
) -> ProcessingJob:
    return ProcessingJob.objects.create(
        submission=submission,
        book=book,
        job_type=job_type,
        status=status,
        queue_name=queue_name,
        task_id=task_id,
        cancel_requested=cancel_requested,
        last_error=last_error,
    )
