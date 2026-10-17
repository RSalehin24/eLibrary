from rest_framework import serializers

from apps.processing.job_models import BackgroundJobKind, BackgroundJobState


class WorkCountsSerializer(serializers.Serializer):
    queued = serializers.IntegerField()
    running = serializers.IntegerField()
    retry_wait = serializers.IntegerField()
    paused = serializers.IntegerField()
    failed = serializers.IntegerField()
    needs_attention = serializers.IntegerField()
    oldest_wait_seconds = serializers.IntegerField(allow_null=True)


class WorkIssueSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=BackgroundJobKind.choices)
    state = serializers.ChoiceField(choices=BackgroundJobState.choices)
    title = serializers.CharField()
    error_code = serializers.CharField()
    finished_at = serializers.DateTimeField(allow_null=True)
    status_url = serializers.CharField()


class WorkSummarySerializer(serializers.Serializer):
    counts = WorkCountsSerializer()
    issues = WorkIssueSerializer(many=True)


class OverviewWorkSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    processing = WorkSummarySerializer(allow_null=True)
    account_mail = WorkSummarySerializer(allow_null=True)


class BookCountsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    draft = serializers.IntegerField()
    processing = serializers.IntegerField()
    ready = serializers.IntegerField()
    published = serializers.IntegerField()
    archived = serializers.IntegerField()
    editorial_pending = serializers.IntegerField(
        help_text="Deprecated compatibility field. Always zero; manual editorial review is not required."
    )


class SourceCountsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    unlinked = serializers.IntegerField()
    linked = serializers.IntegerField()
    removed = serializers.IntegerField()


class AccountCountsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    setup_pending = serializers.IntegerField()


class ManagementOverviewSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    books = BookCountsSerializer(allow_null=True)
    sources = SourceCountsSerializer(allow_null=True)
    accounts = AccountCountsSerializer(allow_null=True)
    work = OverviewWorkSerializer()
