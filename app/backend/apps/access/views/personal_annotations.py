from typing import ClassVar

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.access.annotation_serializers import (
    AnnotationUpdateSerializer,
    BookmarkDetailSerializer,
    BookmarkSummarySerializer,
    HighlightDetailSerializer,
    HighlightSummarySerializer,
    PersonalAnnotationParametersSerializer,
    PersonalBookmarksSerializer,
    PersonalHighlightsSerializer,
)
from apps.access.models import Bookmark, Highlight
from apps.access.reading.annotations import (
    annotation_page,
    annotation_summaries,
    personal_annotations,
    update_annotation,
)
from apps.common.api import VersionedAPIView

from .reader_annotations import collection_response


def personal_annotation_page(request, model):
    parameters = PersonalAnnotationParametersSerializer(data=request.query_params)
    parameters.is_valid(raise_exception=True)
    book = parameters.validated_data.get("book", "")
    scope = f"personal:{model._meta.label}:{request.user.pk}:{book}"
    queryset = personal_annotations(request.user, model)
    if book:
        queryset = queryset.filter(book__slug=book)
    return annotation_page(
        annotation_summaries(queryset),
        parameters.validated_data,
        scope,
    )


class PersonalBookmarksView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="personal_bookmarks",
        parameters=[PersonalAnnotationParametersSerializer],
        responses={200: PersonalBookmarksSerializer},
    )
    def get(self, request):
        entries, cursor = personal_annotation_page(request, Bookmark)
        return collection_response(entries, cursor, BookmarkSummarySerializer)


class PersonalHighlightsView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="personal_highlights",
        parameters=[PersonalAnnotationParametersSerializer],
        responses={200: PersonalHighlightsSerializer},
    )
    def get(self, request):
        entries, cursor = personal_annotation_page(request, Highlight)
        return collection_response(entries, cursor, HighlightSummarySerializer)


class PersonalAnnotationDetailView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)
    model: ClassVar[type[Bookmark] | type[Highlight]] = Bookmark
    serializer_class: ClassVar[
        type[BookmarkDetailSerializer] | type[HighlightDetailSerializer]
    ] = BookmarkDetailSerializer

    def get(self, request, annotation_id):
        annotation = get_object_or_404(
            personal_annotations(request.user, self.model), pk=annotation_id
        )
        return Response(self.serializer_class(annotation).data)

    @extend_schema(request=AnnotationUpdateSerializer)
    def patch(self, request, annotation_id):
        serializer = AnnotationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        annotation = update_annotation(
            personal_annotations(request.user, self.model),
            annotation_id,
            serializer.validated_data,
        )
        return Response(self.serializer_class(annotation).data)

    @extend_schema(responses={204: None})
    def delete(self, request, annotation_id):
        annotation = get_object_or_404(
            personal_annotations(request.user, self.model), pk=annotation_id
        )
        annotation.delete()
        return Response(status=204)


class PersonalBookmarkDetailView(PersonalAnnotationDetailView):
    pass


class PersonalHighlightDetailView(PersonalAnnotationDetailView):
    model = Highlight
    serializer_class = HighlightDetailSerializer
