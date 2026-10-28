from typing import ClassVar

from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class SavedBook(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="saved_books"
    )
    book = models.ForeignKey(
        "catalog.Book", on_delete=models.CASCADE, related_name="saved_by"
    )

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(fields=["user", "book"], name="unique_saved_book")
        ]
