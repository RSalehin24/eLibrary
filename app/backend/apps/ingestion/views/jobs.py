import json

from django.db.models import Count
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.renderers import BaseRenderer

from apps.common.permissions import CanManageProcessing
from apps.ingestion.engine.constants import (
    CH_JOB_ASSIGNED,
    CH_JOB_COMPLETED,
    CH_JOB_REASSIGNED,
)
from apps.ingestion.engine.redis_client import create_redis_client
from apps.ingestion.models import JobStatus, JobType
from apps.ingestion.serializers import ProcessingJobSerializer, ProcessingLogSerializer
from apps.ingestion.services.submissions import recover_stale_processing_jobs


class EventStreamRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "event-stream"
    charset = "utf-8"
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data if data is not None else b""

from .filters import apply_created_at_filters, apply_limit, apply_submission_origin_filter, apply_text_search, normalize_status_filter
from .querysets import jobs_ordered_queryset, visible_jobs_queryset


class ProcessingJobListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessingJobSerializer

    def get_queryset(self):
        queryset = visible_jobs_queryset(self.request.user)
        queryset = apply_submission_origin_filter(queryset, self.request.query_params.get("origin", "").strip(), field_name="submission__origin")
        status_raw = self.request.query_params.get("status", "").strip()
        if status_raw:
            status_values = [normalize_status_filter(s.strip()) for s in status_raw.split(",") if s.strip()]
            if len(status_values) == 1:
                queryset = queryset.filter(status=status_values[0])
            elif status_values:
                queryset = queryset.filter(status__in=status_values)
        submission_status = normalize_status_filter(self.request.query_params.get("submission_status", "").strip())
        if submission_status:
            queryset = queryset.filter(submission__status=submission_status)
        job_type = self.request.query_params.get("job_type", "").strip()
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = apply_text_search(queryset, query, "submission__original_input", "last_error", "book__title")
        queryset = apply_created_at_filters(queryset, self.request)
        return apply_limit(jobs_ordered_queryset(queryset), self.request)


class ProcessingJobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        job = get_object_or_404(visible_jobs_queryset(request.user), pk=pk)
        if job.status in {JobStatus.QUEUED, JobStatus.PROCESSING}:
            return Response({"detail": "Stop this job before deleting it."}, status=status.HTTP_400_BAD_REQUEST)
        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProcessingJobLogsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(visible_jobs_queryset(request.user), pk=pk)
        logs = job.logs.order_by("created_at")[:200]
        return Response(ProcessingLogSerializer(logs, many=True).data)


class ProcessingJobRecoverView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        origin = request.data.get("origin") or request.query_params.get("origin") or ""
        try:
            limit = int(request.data.get("limit") or request.query_params.get("limit") or 50)
        except (TypeError, ValueError):
            return Response({"detail": "limit must be a whole number."}, status=status.HTTP_400_BAD_REQUEST)
        recovered = recover_stale_processing_jobs(origin=origin, limit=max(1, min(limit, 100)))
        return Response({"recovered_jobs": recovered}, status=status.HTTP_202_ACCEPTED)


class ReprocessJobSummaryView(APIView):
    permission_classes = [CanManageProcessing]

    def get(self, request):
        base = visible_jobs_queryset(request.user).filter(job_type=JobType.REPROCESS)
        counts = {row["status"]: row["n"] for row in base.values("status").annotate(n=Count("id"))}
        return Response({
            "queued": counts.get(JobStatus.QUEUED, 0),
            "active": counts.get(JobStatus.PROCESSING, 0),
            "done": counts.get(JobStatus.SUCCEEDED, 0),
            "failed": counts.get(JobStatus.FAILED, 0),
            "stopped": counts.get(JobStatus.CANCELLED, 0),
        })


class ProcessingJobStreamView(APIView):
    """SSE endpoint that streams real-time reprocessing job updates via Engine events."""

    permission_classes = [CanManageProcessing]
    renderer_classes = [EventStreamRenderer]

    def get(self, request):
        def stream():
            redis = create_redis_client()
            pubsub = redis.pubsub()
            pubsub.subscribe(CH_JOB_ASSIGNED, CH_JOB_COMPLETED, CH_JOB_REASSIGNED)
            try:
                yield "event: connected\ndata: {}\n\n"
                while True:
                    message = pubsub.get_message(timeout=5.0)
                    if message and message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                        except (json.JSONDecodeError, TypeError):
                            data = {}
                        yield f"event: job-update\ndata: {json.dumps(data)}\n\n"
                    else:
                        yield ": keepalive\n\n"
            except GeneratorExit:
                pass
            finally:
                try:
                    pubsub.close()
                except Exception:
                    pass
                try:
                    redis.close()
                except Exception:
                    pass

        response = StreamingHttpResponse(stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


__all__ = [
    "ProcessingJobDetailView",
    "ProcessingJobListView",
    "ProcessingJobLogsView",
    "ProcessingJobRecoverView",
    "ProcessingJobStreamView",
    "ReprocessJobSummaryView",
]
