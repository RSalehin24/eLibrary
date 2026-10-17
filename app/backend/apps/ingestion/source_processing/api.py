from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.permissions import CanManageProcessing
from apps.common.validation import reject_unknown_fields
from apps.processing.api_v1 import COMMAND_RESPONSES, accepted_operation
from apps.processing.job_serializers import (
    BackgroundBookSerializer,
    PreparationCommandSerializer,
)

from .commands import request_source_processing
from .issues import source_issue
from .resolution import resolve_source_job
from .verification_serializers import SourceVerificationSerializer


class SourceProcessingCommandSerializer(PreparationCommandSerializer):
    def validate(self, attrs):
        reject_unknown_fields(self)
        return attrs


class ProcessSourceView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageProcessing)

    @extend_schema(
        operation_id="process_source",
        request=SourceProcessingCommandSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request, identifier):
        parameters = SourceProcessingCommandSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        values = parameters.validated_data
        job = request_source_processing(
            request.user,
            (values["operation_id"], identifier),
            values["expected_updated_at"],
        )
        return accepted_operation(job)


class SourceCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackgroundBookSerializer.Meta.model
        fields = (*BackgroundBookSerializer.Meta.fields, "catalog_code", "updated_at")
        read_only_fields = fields


class SourceIssueSerializer(serializers.Serializer):
    verification = SourceVerificationSerializer(allow_null=True)
    id = serializers.UUIDField()
    expected_updated_at = serializers.DateTimeField()
    title = serializers.CharField()
    author_line = serializers.CharField()
    validation_status = serializers.CharField()
    error_count = serializers.IntegerField()
    warning_count = serializers.IntegerField()
    candidates = SourceCandidateSerializer(many=True)
    available_choices = serializers.ListField(child=serializers.CharField())


class SourceResolutionSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    choice = serializers.ChoiceField(
        choices=["retry", "link", "separate", "resume_preparation", "cancel"]
    )
    book_id = serializers.UUIDField(required=False)
    expected_book_updated_at = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        reject_unknown_fields(self)
        if attrs["choice"] == "link" and not attrs.get("book_id"):
            raise serializers.ValidationError({"book_id": "Choose the matching book."})
        if attrs["choice"] == "link" and not attrs.get("expected_book_updated_at"):
            raise serializers.ValidationError(
                {
                    "expected_book_updated_at": "Inspect the current candidate before linking."
                }
            )
        return attrs


class SourceIssueView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageProcessing)

    @extend_schema(
        operation_id="source_issue",
        responses={
            200: SourceIssueSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, identifier):
        return Response(SourceIssueSerializer(source_issue(identifier)).data)

    @extend_schema(
        operation_id="source_issue_resolve",
        request=SourceResolutionSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request, identifier):
        parameters = SourceResolutionSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        return accepted_operation(
            resolve_source_job(request.user, identifier, parameters.validated_data)
        )
