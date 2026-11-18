from urllib.parse import quote

from apps.ingestion import views as ingestion_views
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import GeneratedAssetStatus, GeneratedAssetType
from apps.common.throttles import SubmissionRateThrottle
from apps.common.url_utils import public_api_url
from apps.ingestion.models import MatchCandidate, ResolutionStatus, SubmissionOrigin, SubmissionStatus
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
    ensure_preview_session,
    find_existing_book_by_source_url,
    fulfill_submission_with_existing_book,
    retry_submission_record,
    retry_submission_records,
    sync_deduplicated_submissions,
)

from .filters import apply_created_at_filters, apply_limit, apply_submission_origin_filter, apply_text_search, normalize_status_filter
from .guards import automation_manual_creation_locked_response
from .querysets import (
    get_accessible_submission,
    has_active_root_jobs,
    is_public_submission,
    submission_base_queryset,
    submissions_ordered_queryset,
    visible_submissions_queryset,
)


class SubmissionListCreateView(APIView):
    def get_permissions(self):
        return [AllowAny()] if self.request.method == "POST" else [IsAuthenticated()]

    def get_throttles(self):
        return [SubmissionRateThrottle()] if self.request.method == "POST" else []

    def get(self, request):
        queryset = visible_submissions_queryset(request.user)
        queryset = apply_submission_origin_filter(queryset, request.query_params.get("origin", "").strip(), field_name="origin")
        status_filter = normalize_status_filter(request.query_params.get("status", "").strip())
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        review_state = request.query_params.get("review_state", "").strip()
        if review_state:
            queryset = queryset.filter(review_state=review_state)
        resolution_status = request.query_params.get("resolution_status", "").strip()
        if resolution_status:
            queryset = queryset.filter(resolution_status=resolution_status)
        input_type = request.query_params.get("input_type", "").strip()
        if input_type:
            queryset = queryset.filter(input_type=input_type)
        query = request.query_params.get("q", "").strip()
        if query:
            queryset = apply_text_search(queryset, query, "original_input", "resolved_url")
        linked_book_slug = request.query_params.get("linked_book_slug", "").strip()
        if linked_book_slug:
            queryset = queryset.filter(linked_book__slug=linked_book_slug)
        queryset = apply_created_at_filters(queryset, request)
        queryset = apply_limit(submissions_ordered_queryset(queryset), request)
        return Response(SubmissionSerializer(queryset, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = SubmissionBatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submissions = create_submission_records(
            submitter=request.user if request.user.is_authenticated else None,
            parsed_entries=serializer.validated_data["parsed_entries"],
            auto_process=serializer.validated_data["auto_process"],
            origin=SubmissionOrigin.USER,
        )
        payload = SubmissionSerializer(submissions, many=True, context={"request": request}).data
        return Response(payload, status=status.HTTP_201_CREATED)


class SubmissionBulkStatusView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_ids = [str(value) for value in serializer.validated_data["ids"]]
        submission_map = {str(submission.id): submission for submission in submission_base_queryset().filter(pk__in=requested_ids)}
        visible_submissions = []
        user = request.user
        can_manage = getattr(user, "is_authenticated", False) and can_manage_processing_records(user)

        for submission_id in requested_ids:
            submission = submission_map.get(submission_id)
            if submission is None:
                continue
            if can_manage or (getattr(user, "is_authenticated", False) and submission.submitter_id == user.id) or is_public_submission(submission):
                visible_submissions.append(submission)

        return Response(SubmissionSerializer(visible_submissions, many=True, context={"request": request}).data)


class SubmissionDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [AllowAny]
    serializer_class = SubmissionSerializer
    lookup_field = "pk"

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "DELETE" else [AllowAny()]

    def get_object(self):
        return get_accessible_submission(self.request, self.kwargs["pk"])

    def destroy(self, request, *args, **kwargs):
        submission = visible_submissions_queryset(request.user).filter(pk=kwargs["pk"]).first()
        if submission is None:
            raise PermissionDenied("You cannot delete this request.")
        try:
            delete_submission_record(submission)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubmissionConfirmCandidateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        submission = get_accessible_submission(request, pk)
        target_submission = submission.canonical_submission or submission
        candidate_id = request.data.get("candidate_id")
        if not candidate_id:
            return Response({"detail": "candidate_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        candidate = get_object_or_404(MatchCandidate.objects.select_related("resolution_attempt__submission"), pk=candidate_id)
        if candidate.resolution_attempt.submission_id != target_submission.id:
            raise PermissionDenied("This candidate does not belong to the specified submission.")

        MatchCandidate.objects.filter(resolution_attempt=candidate.resolution_attempt).update(is_selected=False)
        candidate.is_selected = True
        candidate.save(update_fields=["is_selected", "updated_at"])

        target_submission.resolved_url = candidate.candidate_url
        target_submission.resolution_status = ResolutionStatus.RESOLVED
        target_submission.resolution_confidence = candidate.confidence
        target_submission.status = SubmissionStatus.QUEUED
        target_submission.error_message = ""
        target_submission.save(update_fields=["resolved_url", "resolution_status", "resolution_confidence", "status", "error_message", "updated_at"])
        sync_deduplicated_submissions(target_submission)

        existing_book = find_existing_book_by_source_url(candidate.candidate_url)
        if existing_book:
            fulfill_submission_with_existing_book(
                target_submission,
                existing_book,
                source="confirmed_candidate_source_url",
                confidence=candidate.confidence,
                resolved_url=candidate.candidate_url,
            )
            return Response(SubmissionSerializer(submission, context={"request": request}).data)

        locked_response = automation_manual_creation_locked_response()
        if locked_response:
            return locked_response
        ingestion_views.queue_submission(target_submission, actor=request.user if request.user.is_authenticated else None)
        return Response(SubmissionSerializer(submission, context={"request": request}).data)


class SubmissionActionLinksView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        submission = get_accessible_submission(request, pk)
        if submission.status != SubmissionStatus.READY or not submission.linked_book_id:
            return Response({"detail": "This submission is not ready yet."}, status=status.HTTP_400_BAD_REQUEST)
        if submission.linked_book.deleted_at:
            return Response({"detail": "This book was deleted."}, status=status.HTTP_410_GONE)

        preview_session = ensure_preview_session(
            request.user if getattr(request.user, "is_authenticated", False) else None,
            submission.linked_book,
            submission=submission,
            allow_guest=is_public_submission(submission),
        )
        if preview_session is None:
            return Response({"detail": "Could not prepare access for this book."}, status=status.HTTP_400_BAD_REQUEST)

        assets = submission.linked_book.generated_assets
        has_epub = assets.filter(asset_type=GeneratedAssetType.EPUB, status=GeneratedAssetStatus.READY).exists()
        has_html = assets.filter(asset_type=GeneratedAssetType.HTML, status=GeneratedAssetStatus.READY).exists()
        manifest_url = public_api_url("access-reader-manifest", kwargs={"token": preview_session.token}, request=request)
        launch_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reader?manifest={quote(manifest_url, safe='')}"
        return Response(
            {
                "book": {"title": submission.linked_book.title, "slug": submission.linked_book.slug},
                "launch_url": launch_url,
                "manifest_url": manifest_url,
                "epub_download_url": public_api_url("access-reader-epub", kwargs={"token": preview_session.token}, request=request) if has_epub else "",
                "html_preview_url": public_api_url("access-reader-html", kwargs={"token": preview_session.token}, request=request) if has_html else "",
                "expires_at": preview_session.expires_at,
            }
        )


class SubmissionBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_ids = serializer.validated_data["ids"]
        submissions = list(visible_submissions_queryset(request.user).filter(pk__in=requested_ids))
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_ids = serializer.validated_data["ids"]
        submissions = list(visible_submissions_queryset(request.user).filter(pk__in=requested_ids))
        locked_response = automation_manual_creation_locked_response()
        if locked_response:
            return locked_response
        payload = retry_submission_records(submissions, request.user)
        return Response({**payload, "skipped_missing": max(len(requested_ids) - len(submissions), 0)}, status=status.HTTP_202_ACCEPTED)


class SubmissionRetryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        submission = visible_submissions_queryset(request.user).get(pk=pk)
        locked_response = automation_manual_creation_locked_response()
        if locked_response:
            return locked_response
        try:
            job = retry_submission_record(submission, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ProcessingJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


__all__ = [
    "SubmissionActionLinksView",
    "SubmissionBulkDeleteView",
    "SubmissionBulkRetryView",
    "SubmissionBulkStatusView",
    "SubmissionConfirmCandidateView",
    "SubmissionDetailView",
    "SubmissionListCreateView",
    "SubmissionRetryView",
]
