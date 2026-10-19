import hashlib
import json

from django.db import transaction
from django.db.models import IntegerField, Q, Value
from django.db.models.functions import Substr
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, ValidationError

from apps.access.models import Bookmark, Highlight
from apps.common.ranked_pagination import ranked_page

from .bookmark_positions import bookmark_chapter_index


class AnnotationConflict(APIException):
    status_code = 409
    default_code = "state_conflict"
    default_detail = "The annotation changed. Refresh before saving."


def session_annotations(session, model):
    return (
        model.objects.filter(user_id=session.user_id, book_id=session.book_id)
        .filter(
            Q(prepared_publication=session.prepared_publication)
            | Q(prepared_publication__isnull=True)
        )
        .select_related("book")
        .only(
            *(field.name for field in model._meta.concrete_fields),
            "book__id",
            "book__title",
            "book__slug",
        )
    )


def annotation_page(queryset, parameters, scope):
    queryset = search_annotations(queryset, parameters.get("q", ""))
    context = hashlib.sha256(
        json.dumps(
            {"scope": scope, "q": parameters.get("q", ""), "ordering": "created_at,id"},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return ranked_page(
        queryset.annotate(search_rank=Value(0, output_field=IntegerField())),
        parameters,
        context,
    )


def search_annotations(queryset, query):
    if query:
        matching = (
            Q(note__icontains=query)
            | Q(chapter_label__icontains=query)
            | Q(book__title__icontains=query)
        )
        if queryset.model is Highlight:
            matching |= Q(text__icontains=query)
        else:
            matching |= Q(label__icontains=query) | Q(preview_text__icontains=query)
        queryset = queryset.filter(matching)
    return queryset


def validate_annotation_chapter(session, values):
    if values["chapter_href"] not in {
        chapter["path"] for chapter in session.prepared_publication.manifest["chapters"]
    }:
        raise ValidationError({"chapter_href": "Choose a chapter from this edition."})


def validate_bookmark_chapter(session, values):
    validate_annotation_chapter(session, values)
    chapter_index = bookmark_chapter_index(values["location"])
    chapters = session.prepared_publication.manifest["chapters"]
    if (
        chapter_index >= len(chapters)
        or chapters[chapter_index]["path"] != values["chapter_href"]
    ):
        raise ValidationError(
            {"location": "The position must match the chosen chapter."}
        )


@transaction.atomic
def save_bookmark(session, values):
    validate_bookmark_chapter(session, values)
    bookmark, _ = Bookmark.objects.get_or_create(
        user_id=session.user_id,
        book_id=session.book_id,
        location=values["location"],
        prepared_publication=session.prepared_publication,
        defaults={
            "label": values.get("chapter_label", ""),
            "chapter_href": values["chapter_href"],
            "chapter_label": values.get("chapter_label", ""),
            "note": values.get("note", ""),
            "preview_text": values.get("preview_text", ""),
        },
    )
    return bookmark


def save_highlight(session, values):
    validate_annotation_chapter(session, values)
    attributes = dict(values)
    attributes["cfi_range"] = json.dumps(attributes.pop("selector"), sort_keys=True)
    return Highlight.objects.create(
        user_id=session.user_id,
        book_id=session.book_id,
        prepared_publication=session.prepared_publication,
        **attributes,
    )


@transaction.atomic
def update_annotation(queryset, identifier, values):
    annotation = get_object_or_404(
        queryset.select_for_update(of=("self",)), pk=identifier
    )
    if annotation.updated_at != values["expected_updated_at"]:
        raise AnnotationConflict()
    properties = {
        key: values[key] for key in ("note", "color", "kind") if key in values
    }
    if not isinstance(annotation, Highlight) and set(properties) - {"note"}:
        raise ValidationError("Only highlights and quotes have a color or kind.")
    for key, value in properties.items():
        setattr(annotation, key, value)
    annotation.save(update_fields=[*properties, "updated_at"])
    return annotation


def personal_annotations(user, model):
    return (
        model.objects.filter(user=user)
        .select_related("book")
        .only(
            *(field.name for field in model._meta.concrete_fields),
            "book__id",
            "book__title",
            "book__slug",
        )
    )


def annotation_summaries(queryset):
    queryset = queryset.annotate(note_preview=Substr("note", 1, 280)).defer("note")
    if queryset.model is Highlight:
        return queryset.annotate(text_preview=Substr("text", 1, 280)).defer(
            "text", "cfi_range", "tags"
        )
    return queryset
