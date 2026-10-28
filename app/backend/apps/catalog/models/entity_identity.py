from typing import ClassVar

from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class EntitySourceBinding(UUIDPrimaryKeyModel, TimeStampedModel):
    namespace = models.CharField(max_length=255)
    source_key = models.CharField(max_length=1000)
    contributor = models.ForeignKey(
        "catalog.Contributor",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="identity_bindings",
    )
    series = models.ForeignKey(
        "catalog.Series",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="identity_bindings",
    )

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["namespace", "source_key"], name="unique_entity_source_identity"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(contributor__isnull=False, series__isnull=True)
                    | models.Q(contributor__isnull=True, series__isnull=False)
                ),
                name="entity_source_identity_one_target",
            ),
        ]
