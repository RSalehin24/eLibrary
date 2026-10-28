from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.editorial.lifecycle import book_controls, remove_managed_book
from apps.catalog.serializers.editorial import ExpectedRevisionSerializer
from apps.catalog.serializers.management import ManagedBookDetailSerializer
from apps.catalog.views.editorial import managed_book_by_slug
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.validation import reject_unknown_fields
from apps.ingestion.source_processing.regeneration import request_book_regeneration
from apps.processing.job_serializers import OperationAcceptedSerializer


class BookControlsSerializer(serializers.Serializer):
    book_revision = serializers.DateTimeField()
    can_regenerate = serializers.BooleanField()
    regeneration_problem = serializers.ChoiceField(
        choices=[
            "processing_access_required",
            "unfinished_work",
            "source_unavailable",
        ],
        allow_null=True,
    )
    can_remove = serializers.BooleanField()
    active_operation_id = serializers.UUIDField(allow_null=True)


class RegenerateBookSerializer(ExpectedRevisionSerializer):
    operation_id = serializers.UUIDField()

    def validate(self, attributes):
        reject_unknown_fields(self)
        return attributes


class RegenerationAcceptedSerializer(OperationAcceptedSerializer):
    book = ManagedBookDetailSerializer()


class ManagedBookControlsView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="managed_book_controls", responses={200: BookControlsSerializer}
    )
    def get(self, request, slug):
        return Response(
            BookControlsSerializer(
                book_controls(request.user, managed_book_by_slug(request.user, slug))
            ).data
        )


class RegenerateManagedBookView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="managed_book_regenerate",
        request=RegenerateBookSerializer,
        responses={
            202: RegenerationAcceptedSerializer,
            **dict.fromkeys((400, 403, 404, 409), APIErrorSerializer),
        },
    )
    def post(self, request, slug):
        book = managed_book_by_slug(request.user, slug)
        parameters = RegenerateBookSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        job = request_book_regeneration(
            request.user, book.pk, parameters.validated_data
        )
        return Response(
            {
                "operation_id": job.pk,
                "status_url": reverse(
                    "api_v1:managed-job-detail", kwargs={"identifier": job.pk}
                ),
                "book": ManagedBookDetailSerializer(
                    managed_book_by_slug(request.user, book.slug)
                ).data,
            },
            status=202,
        )


def remove_book_response(request, slug):
    parameters = ExpectedRevisionSerializer(data=request.data)
    parameters.is_valid(raise_exception=True)
    reject_unknown_fields(parameters)
    book = managed_book_by_slug(request.user, slug)
    remove_managed_book(
        request.user, book.pk, parameters.validated_data["expected_updated_at"]
    )
    return Response(status=204)
