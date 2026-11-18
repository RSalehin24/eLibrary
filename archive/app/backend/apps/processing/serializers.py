from urllib.parse import unquote, urlparse

from rest_framework import serializers

from .models import (
    BookCreationRequest,
    BookRecord,
    ProcessingAutomationKind,
    ProcessingAutomationSettings,
    ProcessingSyncState,
)
from .services import latest_request_for_record, record_is_selectable, sync_run_mode


class BookRecordSerializer(serializers.ModelSerializer):
    bookCreationState = serializers.CharField(source="book_creation_state")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    displayUrl = serializers.SerializerMethodField()
    displayPath = serializers.SerializerMethodField()
    wasIncomplete = serializers.BooleanField(source="was_incomplete")
    resolvedFromIncomplete = serializers.BooleanField(source="resolved_from_incomplete")
    willResolveToCategory = serializers.CharField(source="will_resolve_to_category")
    isDuplicate = serializers.BooleanField(source="is_duplicate")
    duplicateOfRecordId = serializers.CharField(source="duplicate_of_record_id", allow_null=True)
    linkedBookId = serializers.CharField(source="linked_book_id", allow_null=True)
    linkedBookSlug = serializers.SerializerMethodField()
    selectable = serializers.SerializerMethodField()
    latestRequestId = serializers.SerializerMethodField()

    class Meta:
        model = BookRecord
        fields = [
            "id",
            "name",
            "url",
            "displayUrl",
            "displayPath",
            "category",
            "writer",
            "translator",
            "composer",
            "publisher",
            "createdAt",
            "updatedAt",
            "bookCreationState",
            "linkedBookId",
            "linkedBookSlug",
            "wasIncomplete",
            "resolvedFromIncomplete",
            "willResolveToCategory",
            "isDuplicate",
            "duplicateOfRecordId",
            "selectable",
            "latestRequestId",
        ]

    def get_selectable(self, obj):
        return record_is_selectable(obj)

    def get_latestRequestId(self, obj):
        request = latest_request_for_record(obj)
        return request.id if request else None

    def get_displayUrl(self, obj):
        return unquote(obj.url or "")

    def get_displayPath(self, obj):
        parsed = urlparse((obj.url or "").strip())
        return unquote(parsed.path).strip("/") or parsed.netloc

    def get_linkedBookSlug(self, obj):
        if obj.linked_book_id and obj.linked_book and obj.linked_book.deleted_at is None:
            return obj.linked_book.slug
        return None


class BookCreationRequestSerializer(serializers.ModelSerializer):
    bookRecordId = serializers.CharField(source="book_record_id")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    progress = serializers.SerializerMethodField()
    errorMessage = serializers.CharField(source="error_message", allow_blank=True)
    isResumed = serializers.BooleanField(source="is_resumed")
    isConfirmedNotDuplicate = serializers.BooleanField(source="is_confirmed_not_duplicate")
    duplicateOfRequestId = serializers.CharField(source="duplicate_of_request_id", allow_null=True)
    duplicateOfRecordId = serializers.CharField(source="duplicate_of_record_id", allow_null=True)
    duplicateConfirmed = serializers.BooleanField(source="duplicate_confirmed")
    linkedBookId = serializers.CharField(source="linked_book_id", allow_null=True)
    linkedBookSlug = serializers.SerializerMethodField()
    pipelineOutcome = serializers.CharField(source="pipeline_outcome")
    hasMultiPageToc = serializers.BooleanField(source="has_multi_page_toc")
    sourceTocPageCount = serializers.IntegerField(source="source_toc_page_count")
    fetchedTocPageCount = serializers.IntegerField(source="fetched_toc_page_count")

    class Meta:
        model = BookCreationRequest
        fields = [
            "id",
            "bookRecordId",
            "state",
            "createdAt",
            "updatedAt",
            "progress",
            "errorMessage",
            "isResumed",
            "isConfirmedNotDuplicate",
            "duplicateOfRequestId",
            "duplicateOfRecordId",
            "duplicateConfirmed",
            "linkedBookId",
            "linkedBookSlug",
            "pipelineOutcome",
            "hasMultiPageToc",
            "sourceTocPageCount",
            "fetchedTocPageCount",
        ]

    def get_progress(self, obj):
        if obj.state == BookCreationRequest.State.PAUSED:
            return obj.progress
        if obj.state == BookCreationRequest.State.FAILED and isinstance(obj.progress, dict):
            validation = obj.progress.get("curatedValidation")
            if validation:
                return {
                    "curatedValidation": validation,
                    "curatedStatus": obj.progress.get("curatedStatus", ""),
                }
        return None

    def get_linkedBookSlug(self, obj):
        if obj.linked_book_id and obj.linked_book and obj.linked_book.deleted_at is None:
            return obj.linked_book.slug
        if (
            obj.book_record_id
            and obj.book_record
            and obj.book_record.linked_book_id
            and obj.book_record.linked_book
            and obj.book_record.linked_book.deleted_at is None
        ):
            return obj.book_record.linked_book.slug
        return None


class ProcessingSyncStateSerializer(serializers.ModelSerializer):
    fetchedCount = serializers.IntegerField(source="fetched_count")
    skippedCount = serializers.IntegerField(source="skipped_count")
    updatedCount = serializers.IntegerField(source="updated_count")
    appendedCount = serializers.IntegerField(source="appended_count")
    remotePages = serializers.JSONField(source="remote_pages")
    pageIndex = serializers.IntegerField(source="page_index")
    runMode = serializers.SerializerMethodField()
    phase = serializers.SerializerMethodField()

    class Meta:
        model = ProcessingSyncState
        fields = [
            "status",
            "progress",
            "fetchedCount",
            "skippedCount",
            "updatedCount",
            "appendedCount",
            "message",
            "remotePages",
            "pageIndex",
            "runMode",
            "phase",
        ]

    def get_runMode(self, obj):
        return sync_run_mode(obj)

    def get_phase(self, obj):
        progress = obj.progress if isinstance(obj.progress, dict) else {}
        return str(progress.get("phase") or "sync")


class ProcessingAutomationSettingsSerializer(serializers.ModelSerializer):
    lastRunAt = serializers.DateTimeField(source="last_run_at", allow_null=True)
    statusMessage = serializers.CharField(source="status_message", allow_blank=True)

    class Meta:
        model = ProcessingAutomationSettings
        fields = [
            "kind",
            "enabled",
            "interval",
            "time",
            "saved",
            "lastRunAt",
            "statusMessage",
        ]


class ProcessingStateSerializer(serializers.Serializer):
    records = BookRecordSerializer(many=True)
    requests = BookCreationRequestSerializer(many=True)
    sync = ProcessingSyncStateSerializer()
    automation = serializers.DictField()


class BulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )


class RequestActionSerializer(BulkIdsSerializer):
    action = serializers.ChoiceField(
        choices=[
            "delete",
            "pause",
            "resume",
            "retry",
            "force_generate",
            "new",
            "new_edition",
            "confirm_duplicate",
            "create_again",
            "recreate",
        ]
    )
    deleteBook = serializers.BooleanField(required=False, default=False)


class SyncStartSerializer(serializers.Serializer):
    remotePages = serializers.ListField(
        child=serializers.ListField(child=serializers.DictField()),
        required=False,
        default=list,
    )


class AutomationUpdateSerializer(serializers.Serializer):
    enabled = serializers.BooleanField(required=False)
    interval = serializers.CharField(required=False, allow_blank=False)
    time = serializers.TimeField(required=False)


__all__ = [
    "AutomationUpdateSerializer",
    "BookCreationRequestSerializer",
    "BookRecordSerializer",
    "BulkIdsSerializer",
    "ProcessingStateSerializer",
    "ProcessingSyncStateSerializer",
    "RequestActionSerializer",
    "SyncStartSerializer",
]
