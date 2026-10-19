from typing import ClassVar

from django.db.models import Count, Q
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
    search_annotations,
    update_annotation,
)
from apps.common.api import VersionedAPIView

from .reader_annotations import collection_response


def personal_annotation_page(request, model):
    parameters = PersonalAnnotationParametersSerializer(data=request.query_params)
    parameters.is_valid(raise_exception=True)
    values = parameters.validated_data
    book = values.get("book", "")
    scope = f"personal:{model._meta.label}:{request.user.pk}:{book}:{values['view']}:{values['color']}"
    queryset = personal_annotations(request.user, model)
    if book:
        queryset = queryset.filter(book__slug=book)
    if model is Highlight:
        if values["view"] in {"highlights", "notes"}:
            queryset = queryset.filter(kind="highlight")
            queryset = (
                queryset.filter(note="")
                if values["view"] == "highlights"
                else queryset.exclude(note="")
            )
        elif values["view"] == "quotes":
            queryset = queryset.filter(kind="quote")
        if values["color"]:
            queryset = queryset.filter(color=values["color"])
    entries, cursor = annotation_page(annotation_summaries(queryset), values, scope)
    return entries, cursor, values


def annotation_counts(user, values):
    highlights = search_annotations(personal_annotations(user, Highlight), values["q"])
    bookmarks = search_annotations(personal_annotations(user, Bookmark), values["q"])
    if values.get("book"):
        highlights = highlights.filter(book__slug=values["book"])
        bookmarks = bookmarks.filter(book__slug=values["book"])
    if values.get("color"):
        highlights = highlights.filter(color=values["color"])
    counts = highlights.aggregate(
        highlights=Count("pk", filter=Q(kind="highlight", note="")),
        notes=Count("pk", filter=Q(kind="highlight") & ~Q(note="")),
        quotes=Count("pk", filter=Q(kind="quote")),
    )
    return {**counts, "bookmarks": bookmarks.count()}


def personal_annotation_response(request, model, serializer):
    entries, cursor, values = personal_annotation_page(request, model)
    response = collection_response(entries, cursor, serializer)
    if values["include_counts"]:
        response.data["counts"] = annotation_counts(request.user, values)
    return response


class PersonalBookmarksView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="personal_bookmarks",
        parameters=[PersonalAnnotationParametersSerializer],
        responses={200: PersonalBookmarksSerializer},
    )
    def get(self, request):
        return personal_annotation_response(
            request, Bookmark, BookmarkSummarySerializer
        )


class PersonalHighlightsView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="personal_highlights",
        parameters=[PersonalAnnotationParametersSerializer],
        responses={200: PersonalHighlightsSerializer},
    )
    def get(self, request):
        return personal_annotation_response(
            request, Highlight, HighlightSummarySerializer
        )


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
