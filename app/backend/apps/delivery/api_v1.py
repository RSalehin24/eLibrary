from django.conf import settings
from django.db.models import IntegerField, Value
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.mail_configuration import kindle_sender_email
from apps.catalog.serializers.public import ReaderPageParametersSerializer
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.ranked_pagination import ranked_page
from apps.delivery.requests import (
    KindleRequest,
    cancel_kindle_delivery,
    configured_recipients,
    kindle_book,
    kindle_mail_configured,
    own_deliveries,
    ready_kindle_asset,
    request_kindle_delivery,
)
from apps.delivery.serializers import (
    KindleCancelSerializer,
    KindleCollectionSerializer,
    KindleOperationSerializer,
    KindleOptionsSerializer,
    KindleRequestSerializer,
)
from apps.processing.job_serializers import OperationAcceptedSerializer

COMMAND_RESPONSES = {
    202: OperationAcceptedSerializer,
    400: APIErrorSerializer,
    403: APIErrorSerializer,
    404: APIErrorSerializer,
    409: APIErrorSerializer,
}


def accepted_delivery(job):
    return Response(
        {
            "operation_id": str(job.pk),
            "status_url": reverse(
                "api_v1:kindle-operation", kwargs={"identifier": job.pk}
            ),
        },
        status=202,
    )


class KindleBookView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="kindle_book_options",
        responses={
            200: KindleOptionsSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def get(self, request, slug):
        book = kindle_book(request.user, slug)
        asset = ready_kindle_asset(book)
        values = {
            "book": book,
            "asset_revision": asset.updated_at,
            "recipients": configured_recipients(request.user),
            "sender_email": kindle_sender_email(),
            "configured": kindle_mail_configured(),
            "max_attachment_bytes": settings.KINDLE_MAX_ATTACHMENT_BYTES,
        }
        return Response(KindleOptionsSerializer(values).data)

    @extend_schema(
        operation_id="kindle_book_request",
        request=KindleRequestSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request, slug):
        parameters = KindleRequestSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        values = parameters.validated_data
        command = KindleRequest(
            values["operation_id"],
            values["expected_updated_at"],
            tuple(values["recipients"]),
        )
        return accepted_delivery(request_kindle_delivery(request.user, slug, command))


class KindleOperationView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="kindle_operation_detail",
        responses={
            200: KindleOperationSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, identifier):
        return Response(
            KindleOperationSerializer(
                get_object_or_404(own_deliveries(request.user), pk=identifier)
            ).data
        )

    @extend_schema(
        operation_id="kindle_operation_cancel",
        request=KindleCancelSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request, identifier):
        parameters = KindleCancelSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        return accepted_delivery(
            cancel_kindle_delivery(
                request.user,
                identifier,
                parameters.validated_data["expected_updated_at"],
            )
        )


class KindleOperationsView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="kindle_operations_list",
        parameters=[ReaderPageParametersSerializer],
        responses={
            200: KindleCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
        },
    )
    def get(self, request):
        parameters = ReaderPageParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        queryset = own_deliveries(request.user).annotate(
            search_rank=Value(0, output_field=IntegerField())
        )
        entries, cursor = ranked_page(
            queryset, parameters.validated_data, f"kindle:{request.user.pk}"
        )
        return Response(
            {
                "entries": KindleOperationSerializer(entries, many=True).data,
                "next_cursor": cursor,
                "has_more": cursor is not None,
            }
        )
