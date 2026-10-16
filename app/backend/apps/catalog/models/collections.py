from typing import ClassVar

from django.db import models

from apps.common.models import LifecycleState, TimeStampedModel, UUIDPrimaryKeyModel
from apps.common.text import clean_display_text, normalize_catalog_text

from .editorial import EditorialMetadata
from .utils import build_unique_slug


class CuratedCollection(UUIDPrimaryKeyModel, TimeStampedModel, EditorialMetadata):
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(
        max_length=255, blank=True, editable=False, default=""
    )
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, blank=True)
    state = models.CharField(
        max_length=32, choices=LifecycleState.choices, default=LifecycleState.DRAFT
    )
    books = models.ManyToManyField(
        "catalog.Book", through="CollectionBook", related_name="curated_collections"
    )

    class Meta:
        ordering: ClassVar = ["name", "id"]

    def save(self, *args, **kwargs):
        self.name = clean_display_text(self.name)
        self.normalized_name = normalize_catalog_text(self.name)
        previous = (
            type(self).objects.filter(pk=self.pk).values_list("name", flat=True).first()
        )
        if not self.slug or previous != self.name:
            self.slug = build_unique_slug(type(self), self.name, self)
        super().save(*args, **kwargs)


class CollectionBook(UUIDPrimaryKeyModel, TimeStampedModel):
    collection = models.ForeignKey(
        CuratedCollection, on_delete=models.CASCADE, related_name="collection_books"
    )
    book = models.ForeignKey(
        "catalog.Book", on_delete=models.CASCADE, related_name="collection_books"
    )
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering: ClassVar = ["position", "id"]
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["collection", "book"], name="unique_collection_book"
            )
        ]
