from django.db import models

from apps.common.models import LifecycleState, ReviewState, SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel
from apps.common.text import clean_display_text, normalize_catalog_text

from .catalog_codes import CATALOG_CODE_LENGTH, build_book_catalog_code, is_book_catalog_code
from .choices import (
    BookRecordType,
    ContributorRole,
    CuratedDocumentStatus,
    CuratedEntityType,
    CuratedSectionType,
    GeneratedAssetStatus,
    GeneratedAssetType,
    ManualBindingType,
)
from .entities import Category, Contributor, Series
from .utils import build_unique_slug, generated_asset_upload_to


class BookGroup(UUIDPrimaryKeyModel, TimeStampedModel):
    """Logical grouping for books that are different editions / translations
    of the same underlying work. Used by duplicate-detection to surface
    sibling books that share a canonical title but differ by edition,
    translator, or publisher."""

    canonical_title = models.CharField(max_length=255)
    normalized_canonical_title = models.CharField(
        max_length=255, db_index=True, editable=False, blank=True, default=""
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["canonical_title"]

    def save(self, *args, **kwargs):
        self.canonical_title = clean_display_text(self.canonical_title)
        self.normalized_canonical_title = normalize_catalog_text(self.canonical_title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.canonical_title


class Book(UUIDPrimaryKeyModel, TimeStampedModel, SoftDeleteModel):
    title = models.CharField(max_length=255)
    normalized_title = models.CharField(max_length=255, db_index=True, editable=False, blank=True, default="")
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, blank=True)
    catalog_code = models.CharField(max_length=CATALOG_CODE_LENGTH, unique=True, db_index=True, blank=True, null=True)
    record_type = models.CharField(max_length=16, choices=BookRecordType.choices, default=BookRecordType.DIGITAL, db_index=True)
    manual_is_compilation = models.BooleanField(default=False)
    manual_binding = models.CharField(max_length=32, choices=ManualBindingType.choices, blank=True)
    manual_publisher = models.CharField(max_length=255, blank=True)
    manual_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    edition = models.CharField(max_length=120, blank=True)
    normalized_edition = models.CharField(
        max_length=120, db_index=True, editable=False, blank=True, default=""
    )
    group = models.ForeignKey(
        BookGroup,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="books",
    )
    summary = models.TextField(blank=True)
    state = models.CharField(max_length=32, choices=LifecycleState.choices, default=LifecycleState.DRAFT)
    review_state = models.CharField(max_length=32, choices=ReviewState.choices, default=ReviewState.PENDING)
    source_site = models.CharField(max_length=100, default="ebanglalibrary.com")
    raw_scraped_metadata = models.JSONField(default=dict, blank=True)
    raw_scrape_payload = models.JSONField(default=dict, blank=True)
    main_content_html = models.TextField(blank=True)
    book_info_html = models.TextField(blank=True)
    dedication_html = models.TextField(blank=True)
    toc = models.JSONField(default=list, blank=True)
    content_items = models.JSONField(default=list, blank=True)
    empty_chapters_count = models.IntegerField(default=0)
    cover_source_url = models.URLField(max_length=1000, blank=True)
    metadata_last_reviewed_at = models.DateTimeField(blank=True, null=True)
    contributors = models.ManyToManyField(Contributor, through="BookContributor", related_name="books")
    series_entries = models.ManyToManyField(Series, through="BookSeries", related_name="books")
    categories = models.ManyToManyField(Category, through="BookCategory", related_name="books")

    class Meta:
        ordering = ["-created_at", "title"]
        constraints = []

    def _should_refresh_slug(self):
        if not self.slug or not self.pk:
            return True
        previous = Book.objects.filter(pk=self.pk).values_list("title", flat=True).first()
        return clean_display_text(previous) != self.title

    def save(self, *args, **kwargs):
        self.title = clean_display_text(self.title)
        self.normalized_title = normalize_catalog_text(self.title)
        self.edition = clean_display_text(self.edition or "")
        self.normalized_edition = normalize_catalog_text(self.edition)
        if self._should_refresh_slug():
            self.slug = build_unique_slug(Book, self.title, self)
        current_code = (self.catalog_code or "").strip().upper()
        self.catalog_code = current_code or None
        super().save(*args, **kwargs)
        if self.catalog_code and is_book_catalog_code(self.catalog_code):
            return
        next_code = build_book_catalog_code(self)
        Book.objects.filter(pk=self.pk).update(catalog_code=next_code)
        self.catalog_code = next_code

    def __str__(self):
        return self.title


class BookContributor(UUIDPrimaryKeyModel, TimeStampedModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="book_contributors")
    contributor = models.ForeignKey(Contributor, on_delete=models.CASCADE, related_name="book_contributions")
    role = models.CharField(max_length=32, choices=ContributorRole.choices, default=ContributorRole.AUTHOR)
    raw_value = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "contributor__name"]
        unique_together = ("book", "contributor", "role")

    def __str__(self):
        return f"{self.book} / {self.contributor} ({self.role})"


class BookSeries(UUIDPrimaryKeyModel, TimeStampedModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="book_series")
    series = models.ForeignKey(Series, on_delete=models.CASCADE, related_name="series_books")
    sort_order = models.PositiveIntegerField(default=0)
    raw_value = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["sort_order", "series__name"]
        unique_together = ("book", "series")

    def __str__(self):
        return f"{self.book} / {self.series}"


class BookCategory(UUIDPrimaryKeyModel, TimeStampedModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="book_categories")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="category_books")
    raw_value = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["category__name"]
        unique_together = ("book", "category")

    def __str__(self):
        return f"{self.book} / {self.category}"


class UserBook(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="my_books")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="user_books")

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "book")

    def __str__(self):
        return f"{self.user} / {self.book}"


class BookSource(UUIDPrimaryKeyModel, TimeStampedModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="source_urls")
    source_url = models.URLField(max_length=1000)
    normalized_source_url = models.URLField(max_length=1000, unique=True)
    source_type = models.CharField(max_length=50, default="ebanglalibrary_book")
    source_title = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=True)
    raw_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.normalized_source_url


class GeneratedAsset(UUIDPrimaryKeyModel, TimeStampedModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="generated_assets")
    asset_type = models.CharField(max_length=16, choices=GeneratedAssetType.choices)
    status = models.CharField(max_length=16, choices=GeneratedAssetStatus.choices, default=GeneratedAssetStatus.PENDING)
    file = models.FileField(upload_to=generated_asset_upload_to, blank=True, max_length=500)
    storage_path = models.CharField(max_length=500, blank=True)
    legacy_path = models.CharField(max_length=500, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    file_size = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=128, blank=True)
    is_protected = models.BooleanField(default=True)
    source_job = models.ForeignKey("ingestion.ProcessingJob", on_delete=models.SET_NULL, blank=True, null=True, related_name="generated_assets")

    class Meta:
        ordering = ["asset_type", "-created_at"]
        unique_together = ("book", "asset_type")

    def __str__(self):
        return f"{self.book} / {self.asset_type}"


class MetadataReview(UUIDPrimaryKeyModel, TimeStampedModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="metadata_reviews")
    state = models.CharField(max_length=32, choices=ReviewState.choices, default=ReviewState.PENDING)
    requested_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, blank=True, null=True, related_name="requested_metadata_reviews")
    reviewer = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, blank=True, null=True, related_name="completed_metadata_reviews")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class MetadataVersion(UUIDPrimaryKeyModel, TimeStampedModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="metadata_versions")
    snapshot = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=50, default="scrape")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, blank=True, null=True, related_name="metadata_versions_created")

    class Meta:
        ordering = ["-created_at"]


class CuratedBookDocument(UUIDPrimaryKeyModel, TimeStampedModel):
    book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="curated_documents",
    )
    source_job = models.ForeignKey(
        "ingestion.ProcessingJob",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="curated_documents",
    )
    source_url = models.URLField(max_length=1000, db_index=True)
    canonical_url = models.URLField(max_length=1000, blank=True)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=24,
        choices=CuratedDocumentStatus.choices,
        default=CuratedDocumentStatus.DRAFT,
        db_index=True,
    )
    structure_type = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=255, blank=True)
    validation_summary = models.JSONField(default=dict, blank=True)
    source_snapshot = models.JSONField(default=dict, blank=True)
    document = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("source_url", "version")

    def __str__(self):
        return f"{self.title or self.source_url} v{self.version}"


class CuratedEntity(UUIDPrimaryKeyModel, TimeStampedModel):
    document = models.ForeignKey(CuratedBookDocument, on_delete=models.CASCADE, related_name="entities")
    entity_type = models.CharField(max_length=32, choices=CuratedEntityType.choices)
    role = models.CharField(max_length=64, blank=True)
    value = models.CharField(max_length=500)
    normalized_value = models.CharField(max_length=500, blank=True, db_index=True)
    source_url = models.URLField(max_length=1000, blank=True)
    source_location = models.CharField(max_length=255, blank=True)
    evidence_text = models.TextField(blank=True)
    confidence = models.FloatField(default=0)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["entity_type", "role", "value"]

    def __str__(self):
        return f"{self.entity_type}:{self.role}:{self.value}"


class CuratedSection(UUIDPrimaryKeyModel, TimeStampedModel):
    document = models.ForeignKey(CuratedBookDocument, on_delete=models.CASCADE, related_name="sections")
    section_id = models.CharField(max_length=160)
    section_type = models.CharField(max_length=32, choices=CuratedSectionType.choices)
    title = models.CharField(max_length=500, blank=True)
    path = models.JSONField(default=list, blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    source_location = models.CharField(max_length=255, blank=True)
    html = models.TextField(blank=True)
    confidence = models.FloatField(default=0)
    sort_order = models.PositiveIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["sort_order", "section_id"]
        unique_together = ("document", "section_id")

    def __str__(self):
        return f"{self.section_type}:{self.title or self.section_id}"


class CuratedEvidence(UUIDPrimaryKeyModel, TimeStampedModel):
    document = models.ForeignKey(CuratedBookDocument, on_delete=models.CASCADE, related_name="evidence")
    entity = models.ForeignKey(CuratedEntity, on_delete=models.CASCADE, blank=True, null=True, related_name="evidence")
    section = models.ForeignKey(CuratedSection, on_delete=models.CASCADE, blank=True, null=True, related_name="evidence")
    value = models.CharField(max_length=500, blank=True)
    entity_type = models.CharField(max_length=32, blank=True)
    role = models.CharField(max_length=64, blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    source_location = models.CharField(max_length=255, blank=True)
    evidence_text = models.TextField(blank=True)
    confidence = models.FloatField(default=0)
    extractor = models.CharField(max_length=120, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
