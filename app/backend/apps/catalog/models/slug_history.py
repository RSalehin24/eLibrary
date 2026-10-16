from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class SlugHistory(UUIDPrimaryKeyModel, TimeStampedModel):
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)

    class Meta:
        abstract = True


class BookSlugHistory(SlugHistory):
    entity = models.ForeignKey(
        "catalog.Book", on_delete=models.CASCADE, related_name="slug_history"
    )


class ContributorSlugHistory(SlugHistory):
    entity = models.ForeignKey(
        "catalog.Contributor", on_delete=models.CASCADE, related_name="slug_history"
    )


class CategorySlugHistory(SlugHistory):
    entity = models.ForeignKey(
        "catalog.Category", on_delete=models.CASCADE, related_name="slug_history"
    )


class SeriesSlugHistory(SlugHistory):
    entity = models.ForeignKey(
        "catalog.Series", on_delete=models.CASCADE, related_name="slug_history"
    )


class CollectionSlugHistory(SlugHistory):
    entity = models.ForeignKey(
        "catalog.CuratedCollection",
        on_delete=models.CASCADE,
        related_name="slug_history",
    )
