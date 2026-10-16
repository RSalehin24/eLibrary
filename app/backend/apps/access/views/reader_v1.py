from django.conf import settings
from django.http import Http404
from django.urls import reverse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.access.protected_files import protected_file_response
from apps.access.reader_serializers import (
    ReaderProgressSerializer,
    ReaderSessionSerializer,
)
from apps.access.reading.epub_paths import InvalidEpub, resource_path
from apps.access.reading.preparation import publication_directory
from apps.access.reading.sessions import (
    account_reader_session,
    launch_prepared_reader,
    reading_state,
)
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer


def reader_session_data(session):
    state = reading_state(session)
    return {
        "id": session.pk,
        "book_title": session.book.title,
        "book_slug": session.book.slug,
        "expires_at": session.expires_at,
        "chapters": session.prepared_publication.manifest["chapters"],
        "resource_base": reader_resource_base(session.pk),
        "reading_progress": ReaderProgressSerializer(state).data,
    }


def reader_resource_base(identifier):
    return reverse(
        "api_v1:reader-resource",
        kwargs={"identifier": identifier, "asset_path": "resource-placeholder"},
    ).removesuffix("resource-placeholder")


class ReaderLaunchView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="reader_launch",
        request=None,
        responses={
            200: ReaderSessionSerializer,
            403: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def post(self, request, slug):
        session = launch_prepared_reader(request.user, slug)
        return Response(reader_session_data(session))


class ReaderSessionView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="reader_session",
        responses={200: ReaderSessionSerializer, 404: APIErrorSerializer},
    )
    def get(self, request, identifier):
        session = account_reader_session(request.user, identifier)
        return Response(reader_session_data(session))


class ReaderProgressView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="reader_progress",
        request=ReaderProgressSerializer,
        responses={200: ReaderProgressSerializer},
    )
    def put(self, request, identifier):
        session = account_reader_session(request.user, identifier)
        serializer = ReaderProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        state = reading_state(session)
        state.last_location = serializer.validated_data["last_location"]
        state.progress_percent = serializer.validated_data["progress_percent"]
        state.save(update_fields=["last_location", "progress_percent", "updated_at"])
        return Response(ReaderProgressSerializer(state).data)


class ReaderResourceView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="reader_resource",
        responses={200: OpenApiTypes.BINARY, 404: APIErrorSerializer},
    )
    def get(self, request, identifier, asset_path):
        session = account_reader_session(request.user, identifier)
        resource_source = settings.FRONTEND_BASE_URL + reader_resource_base(session.pk)
        return protected_resource_response(
            session.prepared_publication, asset_path, resource_source
        )


def protected_resource_response(publication, asset_path, resource_source):
    try:
        path = resource_path(asset_path)
    except InvalidEpub as exc:
        raise Http404("Invalid resource path.") from exc
    resource = next(
        (entry for entry in publication.manifest["resources"] if entry["path"] == path),
        None,
    )
    target = publication_directory(publication) / path
    if resource is None or not target.is_file():
        raise Http404("Reader resource not found.")
    response = protected_file_response(target, resource["media_type"])
    response["Content-Security-Policy"] = (
        f"default-src 'none'; img-src {resource_source} data:; "
        f"style-src {resource_source} 'unsafe-inline'; font-src {resource_source}; "
        "frame-ancestors 'self'; base-uri 'none'; form-action 'none'; sandbox allow-same-origin"
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Frame-Options"] = "SAMEORIGIN"
    response["Referrer-Policy"] = "no-referrer"
    return response
