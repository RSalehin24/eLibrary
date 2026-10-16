from rest_framework import serializers

from apps.common.api_serializers import AdminPaginationSerializer
from apps.common.validation import reject_unknown_fields
from apps.processing.job_models import BackgroundJobState, RequestedJobAction
from apps.processing.jobs.queries import available_job_actions


class InvitationSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    email = serializers.EmailField(max_length=254)
    full_name = serializers.CharField(max_length=255, allow_blank=True, default="")
    totp_required = serializers.BooleanField(default=False)

    def validate(self, attrs):
        reject_unknown_fields(self)
        attrs["email"] = attrs["email"].lower()
        return attrs


class ResendInvitationSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    expected_updated_at = serializers.DateTimeField()

    def validate(self, attrs):
        reject_unknown_fields(self)
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)

    def validate(self, attrs):
        reject_unknown_fields(self)
        return attrs


class PasswordResetAcceptedSerializer(serializers.Serializer):
    detail = serializers.CharField()


class AccountMailOperationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    account_id = serializers.IntegerField()
    state = serializers.ChoiceField(choices=BackgroundJobState.choices)
    requested_action = serializers.ChoiceField(choices=RequestedJobAction.choices)
    actions = serializers.SerializerMethodField()
    error_code = serializers.CharField()
    attempt_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField(allow_null=True)
    accepted_at = serializers.DateTimeField(
        source="checkpoint.accepted_at", default=None, read_only=True, allow_null=True
    )

    def get_actions(self, job) -> list[str]:
        return available_job_actions(job)


class AccountMailCollectionSerializer(serializers.Serializer):
    entries = AccountMailOperationSerializer(many=True)
    pagination = AdminPaginationSerializer()
