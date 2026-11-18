from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel
from apps.common.text import clean_display_text, clean_entity_display_text, normalize_catalog_text

from .catalog_codes import (
    CATEGORY_ENTITY_TAG,
    CATALOG_CODE_LENGTH,
    SERIES_ENTITY_TAG,
    WRITER_ENTITY_TAG,
    build_category_catalog_code,
    build_series_catalog_code,
    build_writer_catalog_code,
    is_entity_catalog_code,
    next_entity_sequence,
)
from .utils import build_unique_slug


class Contributor(UUIDPrimaryKeyModel, TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    normalized_name = models.CharField(max_length=255, unique=True, db_index=True, editable=False, blank=True, default="")
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, blank=True)
    catalog_code = models.CharField(max_length=CATALOG_CODE_LENGTH, unique=True, db_index=True, blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def _should_refresh_slug(self):
        if not self.slug or not self.pk:
            return True
        previous = Contributor.objects.filter(pk=self.pk).values_list("name", flat=True).first()
        return clean_display_text(previous) != self.name

    def save(self, *args, **kwargs):
        self.name = clean_entity_display_text(self.name)
        self.normalized_name = normalize_catalog_text(self.name)
        if self._should_refresh_slug():
            self.slug = build_unique_slug(Contributor, self.name, self)
        current_code = (self.catalog_code or "").strip().upper()
        if current_code and is_entity_catalog_code(current_code, entity_tag=WRITER_ENTITY_TAG):
            self.catalog_code = current_code
        else:
            self.catalog_code = build_writer_catalog_code(next_entity_sequence(Contributor, "catalog_code", entity_tag=WRITER_ENTITY_TAG, exclude_pk=self.pk))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Series(UUIDPrimaryKeyModel, TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    normalized_name = models.CharField(max_length=255, unique=True, db_index=True, editable=False, blank=True, default="")
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, blank=True)
    catalog_code = models.CharField(max_length=CATALOG_CODE_LENGTH, unique=True, db_index=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "series"
        ordering = ["name"]

    def _should_refresh_slug(self):
        if not self.slug or not self.pk:
            return True
        previous = Series.objects.filter(pk=self.pk).values_list("name", flat=True).first()
        return clean_display_text(previous) != self.name

    def save(self, *args, **kwargs):
        self.name = clean_entity_display_text(self.name)
        self.normalized_name = normalize_catalog_text(self.name)
        if self._should_refresh_slug():
            self.slug = build_unique_slug(Series, self.name, self)
        current_code = (self.catalog_code or "").strip().upper()
        if current_code and is_entity_catalog_code(current_code, entity_tag=SERIES_ENTITY_TAG):
            self.catalog_code = current_code
        else:
            self.catalog_code = build_series_catalog_code(next_entity_sequence(Series, "catalog_code", entity_tag=SERIES_ENTITY_TAG, exclude_pk=self.pk))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(UUIDPrimaryKeyModel, TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    normalized_name = models.CharField(max_length=255, unique=True, db_index=True, editable=False, blank=True, default="")
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, blank=True)
    catalog_code = models.CharField(max_length=CATALOG_CODE_LENGTH, unique=True, db_index=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def _should_refresh_slug(self):
        if not self.slug or not self.pk:
            return True
        previous = Category.objects.filter(pk=self.pk).values_list("name", flat=True).first()
        return clean_display_text(previous) != self.name

    def save(self, *args, **kwargs):
        self.name = clean_entity_display_text(self.name)
        self.normalized_name = normalize_catalog_text(self.name)
        if self._should_refresh_slug():
            self.slug = build_unique_slug(Category, self.name, self)
        current_code = (self.catalog_code or "").strip().upper()
        if current_code and is_entity_catalog_code(current_code, entity_tag=CATEGORY_ENTITY_TAG):
            self.catalog_code = current_code
        else:
            self.catalog_code = build_category_catalog_code(next_entity_sequence(Category, "catalog_code", entity_tag=CATEGORY_ENTITY_TAG, exclude_pk=self.pk))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
