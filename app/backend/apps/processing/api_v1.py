from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from apps.catalog.models import Book
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.pagination import BoundedAdminPagination
from apps.common.permissions import CanManageProcessing
from apps.processing.job_models import BackgroundJob
from apps.processing.job_serializers import (
    BackgroundJobCollectionSerializer,
    BackgroundJobDetailSerializer,
    BackgroundJobSerializer,
    JobControlSerializer,
    JobParametersSerializer,
    OperationAcceptedSerializer,
    PreparationCommandSerializer,
    ProcessingAssetSerializer,
)
from apps.processing.jobs.filters import filtered_jobs
from apps.processing.jobs.queries import job_detail_queryset, job_queryset
from apps.processing.jobs.requests import (
    JobControlRequest,
    PreparationRequest,
    control_background_job,
    request_preparation,
)
from apps.processing.managed_assets import processing_assets

COMMAND_RESPONSES = {
    202: OperationAcceptedSerializer,
    400: APIErrorSerializer,
    403: APIErrorSerializer,
    404: APIErrorSerializer,
    409: APIErrorSerializer,
}


def accepted_operation(job):
    url = reverse("api_v1:managed-job-detail", kwargs={"identifier": job.pk})
    return Response({"operation_id": str(job.pk), "status_url": url}, status=202)


class BackgroundJobListView(VersionedAPIView):
    permission_classes = (CanManageProcessing,)

    @extend_schema(
        operation_id="managed_jobs_list",
        parameters=[JobParametersSerializer],
        responses={
            200: BackgroundJobCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
        },
    )
    def get(self, request):
        parameters = JobParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        pagination = BoundedAdminPagination()
        entries: list[BackgroundJob] | None = pagination.paginate_queryset(
            filtered_jobs(job_queryset(request.user), parameters.validated_data),
            request,
            view=self,
        )
        return pagination.get_paginated_response(
            BackgroundJobSerializer(entries, many=True).data
        )


class BackgroundJobDetailView(VersionedAPIView):
    permission_classes = (CanManageProcessing,)

    @extend_schema(
        operation_id="managed_job_detail",
        responses={
            200: BackgroundJobDetailSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, identifier):
        job = get_object_or_404(job_detail_queryset(request.user), pk=identifier)
        return Response(BackgroundJobDetailSerializer(job).data)

    @extend_schema(
        operation_id="managed_job_control",
        request=JobControlSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request, identifier):
        parameters = JobControlSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        command = JobControlRequest(identifier=identifier, **parameters.validated_data)
        return accepted_operation(control_background_job(request.user, command))


class ProcessingAssetListView(VersionedAPIView):
    permission_classes = (CanManageProcessing,)

    @extend_schema(
        operation_id="managed_book_assets",
        responses={
            200: ProcessingAssetSerializer(many=True),
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, slug):
        book = get_object_or_404(
            Book.objects.filter(deleted_at__isnull=True), slug=slug
        )
        return Response(
            ProcessingAssetSerializer(
                processing_assets(book, request.user), many=True
            ).data
        )


class PrepareAssetView(VersionedAPIView):
    permission_classes = (CanManageProcessing,)

    @extend_schema(
        operation_id="managed_asset_prepare",
        request=PreparationCommandSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request, identifier):
        parameters = PreparationCommandSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        values = parameters.validated_data
        command = PreparationRequest(
            values["operation_id"], identifier, values["expected_updated_at"]
        )
        return accepted_operation(request_preparation(request.user, command))
