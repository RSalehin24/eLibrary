from typing import ClassVar

from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttles import SubmissionRateThrottle
from apps.ingestion.models import (
    SubmissionOrigin,
)
from apps.ingestion.serializers import (
    BulkIdsSerializer,
    ProcessingJobSerializer,
    SubmissionBatchCreateSerializer,
    SubmissionSerializer,
)
from apps.ingestion.services.submissions import (
    can_manage_processing_records,
    create_submission_records,
    delete_submission_record,
    retry_submission_record,
    retry_submission_records,
)

from .filters import (
    apply_created_at_filters,
    apply_limit,
    apply_submission_origin_filter,
    apply_text_search,
    normalize_status_filter,
)
from .guards import automation_manual_creation_locked_response
from .querysets import (
    get_accessible_submission,
    is_public_submission,
    submission_base_queryset,
    submissions_ordered_queryset,
    visible_submissions_queryset,
)
from .submission_links import SubmissionActionLinksView


class SubmissionListCreateView(APIView):
    def get_permissions(self):
        return [AllowAny()] if self.request.method == "POST" else [IsAuthenticated()]

    def get_throttles(self):
        return [SubmissionRateThrottle()] if self.request.method == "POST" else []

    def get(self, request):
        queryset = visible_submissions_queryset(request.user)
        queryset = apply_submission_origin_filter(
            queryset,
            request.query_params.get("origin", "").strip(),
            field_name="origin",
        )
        status_filter = normalize_status_filter(
            request.query_params.get("status", "").strip()
        )
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        resolution_status = request.query_params.get("resolution_status", "").strip()
        if resolution_status:
            queryset = queryset.filter(resolution_status=resolution_status)
        input_type = request.query_params.get("input_type", "").strip()
        if input_type:
            queryset = queryset.filter(input_type=input_type)
        query = request.query_params.get("q", "").strip()
        if query:
            queryset = apply_text_search(
                queryset, query, "original_input", "resolved_url"
            )
        linked_book_slug = request.query_params.get("linked_book_slug", "").strip()
        if linked_book_slug:
            queryset = queryset.filter(linked_book__slug=linked_book_slug)
        queryset = apply_created_at_filters(queryset, request)
        queryset = apply_limit(submissions_ordered_queryset(queryset), request)
        return Response(
            SubmissionSerializer(queryset, many=True, context={"request": request}).data
        )

    def post(self, request):
        serializer = SubmissionBatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submissions = create_submission_records(
            submitter=request.user if request.user.is_authenticated else None,
            parsed_entries=serializer.validated_data["parsed_entries"],
            auto_process=serializer.validated_data["auto_process"],
            origin=SubmissionOrigin.USER,
        )
        payload = SubmissionSerializer(
            submissions, many=True, context={"request": request}
        ).data
        return Response(payload, status=status.HTTP_201_CREATED)


class SubmissionBulkStatusView(APIView):
    permission_classes: ClassVar = [AllowAny]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_ids = [str(value) for value in serializer.validated_data["ids"]]
        submission_map = {
            str(submission.id): submission
            for submission in submission_base_queryset().filter(pk__in=requested_ids)
        }
        visible_submissions = []
        user = request.user
        can_manage = getattr(
            user, "is_authenticated", False
        ) and can_manage_processing_records(user)

        for submission_id in requested_ids:
            submission = submission_map.get(submission_id)
            if submission is None:
                continue
            if (
                can_manage
                or (
                    getattr(user, "is_authenticated", False)
                    and submission.submitter_id == user.id
                )
                or is_public_submission(submission)
            ):
                visible_submissions.append(submission)

        return Response(
            SubmissionSerializer(
                visible_submissions, many=True, context={"request": request}
            ).data
        )


class SubmissionDetailView(generics.RetrieveDestroyAPIView):
    permission_classes: ClassVar = [AllowAny]
    serializer_class = SubmissionSerializer
    lookup_field = "pk"

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "DELETE" else [AllowAny()]

    def get_object(self):
        return get_accessible_submission(self.request, self.kwargs["pk"])

    def destroy(self, request, *args, **kwargs):
        submission = (
            visible_submissions_queryset(request.user).filter(pk=kwargs["pk"]).first()
        )
        if submission is None:
            raise PermissionDenied("You cannot delete this request.")
        try:
            delete_submission_record(submission)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubmissionBulkDeleteView(APIView):
    permission_classes: ClassVar = [IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_ids = serializer.validated_data["ids"]
        submissions = list(
            visible_submissions_queryset(request.user).filter(pk__in=requested_ids)
        )
        deleted_count = 0
        soft_deleted_count = 0
        hard_deleted_count = 0
        skipped_active = 0
        skipped_missing = len(requested_ids) - len(submissions)
        seen_target_ids = set()
        for submission in submissions:
            target_id = str(submission.canonical_submission_id or submission.id)
            if target_id in seen_target_ids:
                continue
            seen_target_ids.add(target_id)
            try:
                delete_mode = delete_submission_record(submission)
            except ValueError:
                skipped_active += 1
                continue
            deleted_count += 1
            if delete_mode == "hard_deleted":
                hard_deleted_count += 1
            else:
                soft_deleted_count += 1
        return Response(
            {
                "deleted_count": deleted_count,
                "soft_deleted_count": soft_deleted_count,
                "hard_deleted_count": hard_deleted_count,
                "skipped_active": skipped_active,
                "skipped_missing": skipped_missing,
            }
        )


class SubmissionBulkRetryView(APIView):
    permission_classes: ClassVar = [IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_ids = serializer.validated_data["ids"]
        submissions = list(
            visible_submissions_queryset(request.user).filter(pk__in=requested_ids)
        )
        locked_response = automation_manual_creation_locked_response()
        if locked_response:
            return locked_response
        payload = retry_submission_records(submissions, request.user)
        return Response(
            {
                **payload,
                "skipped_missing": max(len(requested_ids) - len(submissions), 0),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class SubmissionRetryView(APIView):
    permission_classes: ClassVar = [IsAuthenticated]

    def post(self, request, pk):
        submission = visible_submissions_queryset(request.user).get(pk=pk)
        locked_response = automation_manual_creation_locked_response()
        if locked_response:
            return locked_response
        try:
            job = retry_submission_record(submission, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            ProcessingJobSerializer(job).data, status=status.HTTP_202_ACCEPTED
        )


__all__ = [
    "SubmissionActionLinksView",
    "SubmissionBulkDeleteView",
    "SubmissionBulkRetryView",
    "SubmissionBulkStatusView",
    "SubmissionDetailView",
    "SubmissionListCreateView",
    "SubmissionRetryView",
]
