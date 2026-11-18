from django.contrib import admin

from .models import (
    BookCreationRequest,
    BookRecord,
    ProcessingAutomationSettings,
    ProcessingSyncState,
    ProcessingUiDomainVersion,
    ProcessingUiProjection,
)


@admin.register(BookRecord)
class BookRecordAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "book_creation_state",
        "writer",
        "publisher",
        "updated_at",
    )
    search_fields = (
        "id",
        "name",
        "url",
        "writer",
        "translator",
        "composer",
        "publisher",
    )
    list_filter = (
        "book_creation_state",
        "category",
        "was_incomplete",
        "resolved_from_incomplete",
        "is_duplicate",
    )
    raw_id_fields = ("linked_book", "duplicate_of_record", "source_catalog_entry")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BookCreationRequest)
class BookCreationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "book_record",
        "origin",
        "state",
        "is_resumed",
        "is_confirmed_not_duplicate",
        "updated_at",
    )
    search_fields = ("id", "book_record__id", "book_record__name", "error_message")
    list_filter = (
        "state",
        "origin",
        "is_resumed",
        "is_confirmed_not_duplicate",
        "duplicate_confirmed",
    )
    raw_id_fields = (
        "book_record",
        "duplicate_of_request",
        "duplicate_of_record",
        "linked_book",
        "submission",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProcessingSyncState)
class ProcessingSyncStateAdmin(admin.ModelAdmin):
    list_display = (
        "singleton_key",
        "status",
        "page_index",
        "fetched_count",
        "updated_count",
        "appended_count",
        "task_id",
        "updated_at",
    )
    search_fields = ("singleton_key", "message", "task_id", "queue_name", "last_error")
    list_filter = ("status",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProcessingAutomationSettings)
class ProcessingAutomationSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "kind",
        "enabled",
        "interval",
        "time",
        "saved",
        "last_run_at",
        "updated_at",
    )
    list_filter = ("kind", "enabled", "saved")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProcessingUiDomainVersion)
class ProcessingUiDomainVersionAdmin(admin.ModelAdmin):
    list_display = ("domain", "version", "updated_at")
    search_fields = ("domain",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProcessingUiProjection)
class ProcessingUiProjectionAdmin(admin.ModelAdmin):
    list_display = ("key", "updated_at")
    search_fields = ("key",)
    readonly_fields = ("created_at", "updated_at")
