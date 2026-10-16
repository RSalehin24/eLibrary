from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.access.annotation_serializers import (
    AnnotationUpdateSerializer,
    BookmarkCollectionSerializer,
    BookmarkCreateSerializer,
    BookmarkDetailSerializer,
    HighlightCollectionSerializer,
    HighlightCreateSerializer,
    HighlightDetailSerializer,
)
from apps.access.models import Bookmark, Highlight
from apps.access.reading.annotations import (
    annotation_page,
    save_bookmark,
    save_highlight,
    session_annotations,
    update_annotation,
)
from apps.access.reading.sessions import account_reader_session
from apps.catalog.serializers.public import CollectionParametersSerializer
from apps.common.api import VersionedAPIView


def session_annotation_page(request, identifier, model):
    session = account_reader_session(request.user, identifier)
    parameters = CollectionParametersSerializer(data=request.query_params)
    parameters.is_valid(raise_exception=True)
    scope = f"{model._meta.label}:{request.user.pk}:{session.book_id}:{session.prepared_publication_id}"
    return annotation_page(
        session_annotations(session, model), parameters.validated_data, scope
    )


def collection_response(entries, cursor, serializer):
    return Response(
        {
            "entries": serializer(entries, many=True).data,
            "next_cursor": cursor,
            "has_more": cursor is not None,
        }
    )


class ReaderBookmarksView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="reader_bookmarks",
        parameters=[CollectionParametersSerializer],
        responses={200: BookmarkCollectionSerializer},
    )
    def get(self, request, identifier):
        entries, cursor = session_annotation_page(request, identifier, Bookmark)
        return collection_response(entries, cursor, BookmarkDetailSerializer)

    @extend_schema(
        operation_id="reader_bookmark_save",
        request=BookmarkCreateSerializer,
        responses={200: BookmarkDetailSerializer},
    )
    def put(self, request, identifier):
        session = account_reader_session(request.user, identifier)
        serializer = BookmarkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bookmark = save_bookmark(session, serializer.validated_data)
        return Response(BookmarkDetailSerializer(bookmark).data)


class ReaderHighlightsView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="reader_highlights",
        parameters=[CollectionParametersSerializer],
        responses={200: HighlightCollectionSerializer},
    )
    def get(self, request, identifier):
        entries, cursor = session_annotation_page(request, identifier, Highlight)
        return collection_response(entries, cursor, HighlightDetailSerializer)

    @extend_schema(
        operation_id="reader_highlight_create",
        request=HighlightCreateSerializer,
        responses={201: HighlightDetailSerializer},
    )
    def post(self, request, identifier):
        session = account_reader_session(request.user, identifier)
        serializer = HighlightCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        annotation = save_highlight(session, serializer.validated_data)
        return Response(HighlightDetailSerializer(annotation).data, status=201)


class ReaderBookmarkDetailView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self, request, identifier):
        return session_annotations(
            account_reader_session(request.user, identifier), Bookmark
        )

    @extend_schema(
        operation_id="reader_bookmark_update",
        request=AnnotationUpdateSerializer,
        responses={200: BookmarkDetailSerializer},
    )
    def patch(self, request, identifier, annotation_id):
        serializer = AnnotationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bookmark = update_annotation(
            self.get_queryset(request, identifier),
            annotation_id,
            serializer.validated_data,
        )
        return Response(BookmarkDetailSerializer(bookmark).data)

    @extend_schema(operation_id="reader_bookmark_delete", responses={204: None})
    def delete(self, request, identifier, annotation_id):
        bookmark = get_object_or_404(
            self.get_queryset(request, identifier), pk=annotation_id
        )
        bookmark.delete()
        return Response(status=204)


class ReaderHighlightDetailView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self, request, identifier):
        return session_annotations(
            account_reader_session(request.user, identifier), Highlight
        )

    @extend_schema(
        operation_id="reader_highlight_update",
        request=AnnotationUpdateSerializer,
        responses={200: HighlightDetailSerializer},
    )
    def patch(self, request, identifier, annotation_id):
        serializer = AnnotationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        annotation = update_annotation(
            self.get_queryset(request, identifier),
            annotation_id,
            serializer.validated_data,
        )
        return Response(HighlightDetailSerializer(annotation).data)

    @extend_schema(operation_id="reader_highlight_delete", responses={204: None})
    def delete(self, request, identifier, annotation_id):
        annotation = get_object_or_404(
            self.get_queryset(request, identifier), pk=annotation_id
        )
        annotation.delete()
        return Response(status=204)
