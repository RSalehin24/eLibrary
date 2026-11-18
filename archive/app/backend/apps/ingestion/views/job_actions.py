from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.models import PermissionScope
from apps.common.permissions import user_has_scope
from apps.ingestion.models import JobStatus, ProcessingJob
from apps.ingestion.serializers import BulkIdsSerializer, ProcessingJobSerializer
from apps.ingestion.services.submissions import cancel_processing_job, resume_processing_job

from .guards import automation_manual_creation_locked_response
from .querysets import visible_jobs_queryset


def can_manage_job(user, job):
    can_manage_processing = user_has_scope(user, [PermissionScope.PROCESSING_MANAGE])
    return user.is_staff or can_manage_processing or job.submission.submitter_id == user.id


class ProcessingJobStopView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(ProcessingJob.objects.select_related("submission"), pk=pk)
        if not can_manage_job(request.user, job):
            raise PermissionDenied("You cannot stop this job.")
        return Response(ProcessingJobSerializer(cancel_processing_job(job)).data)


class ProcessingJobResumeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(ProcessingJob.objects.select_related("submission"), pk=pk)
        if not can_manage_job(request.user, job):
            raise PermissionDenied("You cannot resume this job.")
        locked_response = automation_manual_creation_locked_response()
        if locked_response:
            return locked_response
        try:
            job = resume_processing_job(job)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ProcessingJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class ProcessingJobBulkStopView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        jobs = list(visible_jobs_queryset(request.user).filter(pk__in=serializer.validated_data["ids"]))
        stopped_count = 0
        skipped_complete = 0
        for job in jobs:
            previous_status = job.status
            job = cancel_processing_job(job)
            if previous_status == job.status and job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
                skipped_complete += 1
                continue
            stopped_count += 1
        return Response(
            {
                "stopped_count": stopped_count,
                "skipped_complete": skipped_complete,
                "skipped_missing": max(len(serializer.validated_data["ids"]) - len(jobs), 0),
            }
        )


class ProcessingJobBulkResumeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        jobs = list(visible_jobs_queryset(request.user).filter(pk__in=serializer.validated_data["ids"]))
        locked_response = automation_manual_creation_locked_response()
        if locked_response:
            return locked_response
        resumed_count = 0
        skipped_invalid = 0
        for job in jobs:
            try:
                resume_processing_job(job)
            except ValueError:
                skipped_invalid += 1
                continue
            resumed_count += 1
        return Response(
            {
                "resumed_count": resumed_count,
                "skipped_invalid": skipped_invalid,
                "skipped_missing": max(len(serializer.validated_data["ids"]) - len(jobs), 0),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ProcessingJobBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        jobs = list(visible_jobs_queryset(request.user).filter(pk__in=serializer.validated_data["ids"]))
        deleted_count = 0
        skipped_active = 0
        for job in jobs:
            if job.status in {JobStatus.QUEUED, JobStatus.PROCESSING}:
                skipped_active += 1
                continue
            job.delete()
            deleted_count += 1
        return Response(
            {
                "deleted_count": deleted_count,
                "skipped_active": skipped_active,
                "skipped_missing": max(len(serializer.validated_data["ids"]) - len(jobs), 0),
            }
        )


__all__ = [
    "ProcessingJobBulkDeleteView",
    "ProcessingJobBulkResumeView",
    "ProcessingJobBulkStopView",
    "ProcessingJobResumeView",
    "ProcessingJobStopView",
]
