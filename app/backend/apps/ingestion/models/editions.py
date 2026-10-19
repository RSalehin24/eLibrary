from typing import ClassVar

from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class SourceEdition(UUIDPrimaryKeyModel, TimeStampedModel):
    operation = models.OneToOneField(
        "processing.BackgroundJob",
        on_delete=models.PROTECT,
        related_name="source_edition",
    )
    book = models.ForeignKey(
        "catalog.Book",
        null=True,
        on_delete=models.PROTECT,
        related_name="source_editions",
    )
    source = models.ForeignKey("ingestion.SourceCatalogEntry", on_delete=models.PROTECT)
    state = models.CharField(
        max_length=16,
        choices=[
            ("collecting", "Collecting"),
            ("validated", "Validated"),
            ("published", "Published"),
            ("quarantined", "Quarantined"),
        ],
        default="collecting",
    )
    validator_version = models.PositiveIntegerField(default=1)
    classification = models.CharField(max_length=32, default="unknown_layout")
    document_reference = models.CharField(max_length=255, blank=True)
    validation_report = models.JSONField(default=dict)
    asset_manifest = models.JSONField(default=dict)


class SourceEditionPage(UUIDPrimaryKeyModel, TimeStampedModel):
    edition = models.ForeignKey(
        SourceEdition, on_delete=models.PROTECT, related_name="pages"
    )
    url = models.URLField(max_length=1000)
    content_hash = models.CharField(max_length=64)
    artifact_reference = models.CharField(max_length=255)
    position = models.PositiveIntegerField()
    fetched_at = models.DateTimeField()

    class Meta:
        ordering: ClassVar = ["position", "id"]
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["edition", "url"], name="edition_page_unique_url"
            )
        ]
