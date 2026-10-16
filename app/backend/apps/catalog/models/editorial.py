from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.common.text import clean_display_text, normalize_catalog_text

MAX_ALTERNATIVE_NAMES = 20
MAX_ALTERNATIVE_NAME_LENGTH = 255


def validate_alternative_names(value):
    if not isinstance(value, list) or len(value) > MAX_ALTERNATIVE_NAMES:
        raise ValidationError("Supply at most 20 verified alternative names.")
    for name in value:
        if (
            not isinstance(name, str)
            or not 0 < len(name) <= MAX_ALTERNATIVE_NAME_LENGTH
        ):
            raise ValidationError(
                "Each alternative name must contain 1–255 characters."
            )
        if not normalize_catalog_text(name):
            raise ValidationError("Alternative names must contain letters or numbers.")


def validate_social_image(value):
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValidationError("Use a public HTTPS image URL without credentials.")


class EditorialMetadata(models.Model):
    editorial_description = models.TextField(blank=True)
    alternative_names = models.JSONField(
        default=list, blank=True, validators=[validate_alternative_names]
    )
    normalized_aliases = models.TextField(blank=True, editable=False, default="")
    seo_title = models.CharField(max_length=160, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    social_image_url = models.URLField(
        max_length=1000, blank=True, validators=[validate_social_image]
    )
    indexing_eligible = models.BooleanField(default=False)
    editorial_reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        validate_alternative_names(self.alternative_names)
        self.normalized_aliases = "\n".join(
            dict.fromkeys(
                normalize_catalog_text(name) for name in self.alternative_names
            )
        )
        if (fields := kwargs.get("update_fields")) and "alternative_names" in fields:
            kwargs["update_fields"] = {*fields, "normalized_aliases"}
        with transaction.atomic():
            super().save(*args, **kwargs)

    @property
    def is_indexable(self):
        return bool(
            self.indexing_eligible
            and self.editorial_reviewed_at
            and clean_display_text(self.editorial_description)
        )
