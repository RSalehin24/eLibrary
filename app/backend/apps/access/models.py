import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


def generate_access_token():
    return secrets.token_urlsafe(32)


def default_preview_expiry():
    return timezone.now() + timedelta(hours=2)


class PermissionScope(models.TextChoices):
    SUBMIT_CREATE = "submit:create", "Submit/create"
    PREVIEW_HTML = "preview:html", "Preview HTML"
    READ_DURABLE = "read:durable", "Durable Read"
    DOWNLOAD_FILE = "download:file", "Download Ebook"
    METADATA_EDIT = "metadata:edit", "Edit Metadata"
    PROCESSING_MANAGE = "processing:manage", "Manage Processing"
    ACCESS_MANAGE = "access:manage", "Manage Access"
    VIEW_SOURCE_RECORDS = "source_records:view", "View Records' Source"
    ADMIN_FULL_CONTROL = "admin:full_control", "Admin/full control"
    SEND_KINDLE = "send:kindle", "Send to Kindle"
    READ_ONCE = "read:once", "Read Once"


ACCOUNT_MANAGEABLE_PERMISSION_SCOPES = (
    PermissionScope.ACCESS_MANAGE,
    PermissionScope.PROCESSING_MANAGE,
    PermissionScope.VIEW_SOURCE_RECORDS,
    PermissionScope.METADATA_EDIT,
    PermissionScope.READ_ONCE,
    PermissionScope.SEND_KINDLE,
    PermissionScope.READ_DURABLE,
    PermissionScope.PREVIEW_HTML,
    PermissionScope.DOWNLOAD_FILE,
)

SCOPED_PERMISSION_SCOPES = (
    PermissionScope.METADATA_EDIT,
    PermissionScope.READ_ONCE,
    PermissionScope.SEND_KINDLE,
    PermissionScope.READ_DURABLE,
    PermissionScope.PREVIEW_HTML,
    PermissionScope.DOWNLOAD_FILE,
)


class PermissionGrantQuerySet(models.QuerySet):
    def active(self):
        now = timezone.now()
        return self.filter(is_active=True).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )

    def active_for_user(self, user):
        return self.active().filter(user=user)


class PermissionGrant(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="permission_grants")
    book = models.ForeignKey(
        "catalog.Book",
        on_delete=models.CASCADE,
        related_name="permission_grants",
        blank=True,
        null=True,
    )
    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.CASCADE,
        related_name="permission_grants",
        blank=True,
        null=True,
    )
    contributor = models.ForeignKey(
        "catalog.Contributor",
        on_delete=models.CASCADE,
        related_name="permission_grants",
        blank=True,
        null=True,
    )
    scope = models.CharField(max_length=32, choices=PermissionScope.choices)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    granted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="grants_issued",
        blank=True,
        null=True,
    )
    notes = models.TextField(blank=True)

    objects = PermissionGrantQuerySet.as_manager()

    class Meta:
        ordering = ["user__email", "scope", "book__title", "category__name", "contributor__name"]

    def __str__(self):
        if self.book_id:
            return f"{self.user} / {self.scope} / {self.book}"
        if self.category_id:
            return f"{self.user} / {self.scope} / {self.category}"
        if self.contributor_id:
            return f"{self.user} / {self.scope} / {self.contributor}"
        return f"{self.user} / {self.scope}"


class PreviewAccessSession(UUIDPrimaryKeyModel, TimeStampedModel):
    token = models.CharField(max_length=128, unique=True, default=generate_access_token)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="preview_sessions",
        blank=True,
        null=True,
    )
    book = models.ForeignKey("catalog.Book", on_delete=models.CASCADE, related_name="preview_sessions")
    source_submission = models.ForeignKey(
        "ingestion.BookSubmission",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="preview_sessions",
    )
    expires_at = models.DateTimeField(default=default_preview_expiry)
    launch_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_active(self):
        return self.expires_at > timezone.now()


class ReadingSession(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="reading_sessions")
    book = models.ForeignKey("catalog.Book", on_delete=models.CASCADE, related_name="reading_sessions")
    preview_session = models.ForeignKey(
        PreviewAccessSession,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reading_sessions",
    )
    last_location = models.CharField(max_length=255, blank=True)
    progress_percent = models.FloatField(default=0.0)
    last_opened_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_opened_at"]
        unique_together = ("user", "book")


class Bookmark(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="bookmarks")
    book = models.ForeignKey("catalog.Book", on_delete=models.CASCADE, related_name="bookmarks")
    location = models.CharField(max_length=255)
    label = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)
    chapter_href = models.CharField(max_length=512, blank=True)
    chapter_label = models.CharField(max_length=255, blank=True)
    preview_text = models.CharField(max_length=280, blank=True)

    class Meta:
        ordering = ["book__title", "-created_at"]
        unique_together = ("user", "book", "location")


class HighlightColor(models.TextChoices):
    YELLOW = "yellow", "Yellow"
    GREEN = "green", "Green"
    BLUE = "blue", "Blue"
    PINK = "pink", "Pink"
    UNDERLINE = "underline", "Underline"


class HighlightKind(models.TextChoices):
    HIGHLIGHT = "highlight", "Highlight"
    QUOTE = "quote", "Quote"


class Highlight(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="highlights")
    book = models.ForeignKey("catalog.Book", on_delete=models.CASCADE, related_name="highlights")
    cfi_range = models.CharField(max_length=1024)
    chapter_href = models.CharField(max_length=512, blank=True)
    chapter_label = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    note = models.TextField(blank=True)
    color = models.CharField(max_length=16, choices=HighlightColor.choices, default=HighlightColor.YELLOW)
    kind = models.CharField(max_length=16, choices=HighlightKind.choices, default=HighlightKind.HIGHLIGHT)
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "book"]),
            models.Index(fields=["user", "kind"]),
        ]


class BookOpeningRecord(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="opening_records")
    book = models.ForeignKey("catalog.Book", on_delete=models.CASCADE, related_name="opening_records")

    class Meta:
        unique_together = ("user", "book")

