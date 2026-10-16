from typing import ClassVar

from django.core.validators import MaxValueValidator, MinValueValidator
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


class PhysicalReadingLog(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="physical_reading_logs"
    )
    book = models.ForeignKey(
        "catalog.Book", on_delete=models.CASCADE, related_name="physical_reading_logs"
    )
    status = models.CharField(
        max_length=16,
        choices=[
            ("unread", "Unread"),
            ("reading", "Reading"),
            ("finished", "Finished"),
        ],
        default="unread",
    )
    current_page = models.PositiveIntegerField(
        default=0, validators=[MaxValueValidator(1000000)]
    )
    total_pages = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(1000000)],
    )
    rating = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(5)]
    )
    started_on = models.DateField(null=True, blank=True)
    finished_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["user", "book"], name="unique_physical_reading_log"
            ),
            models.CheckConstraint(
                condition=models.Q(total_pages__isnull=True)
                | models.Q(
                    total_pages__gte=1, current_page__lte=models.F("total_pages")
                ),
                name="physical_reading_valid_pages",
            ),
            models.CheckConstraint(
                condition=models.Q(rating__lte=5), name="physical_reading_valid_rating"
            ),
            models.CheckConstraint(
                condition=models.Q(started_on__isnull=True)
                | models.Q(finished_on__isnull=True)
                | models.Q(started_on__lte=models.F("finished_on")),
                name="physical_reading_valid_dates",
            ),
        ]
