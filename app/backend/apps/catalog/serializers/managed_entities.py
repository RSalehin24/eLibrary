from typing import ClassVar

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.editorial.entity_policy import ENTITY_KINDS
from apps.catalog.models import Contributor, ContributorRole
from apps.catalog.serializers.editorial import (
    EDITORIAL_DETAIL_FIELDS,
    EDITORIAL_FIELDS,
    BookEditorialUpdateSerializer,
    VerifiedAlternativeNamesField,
)
from apps.common.api_serializers import AdminPaginationSerializer
from apps.common.validation import reject_unknown_fields


class CatalogReferenceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class ManagedEntityListSerializer(serializers.ModelSerializer):
    state = serializers.CharField(read_only=True, default="")

    class Meta:
        model = Contributor
        fields = ("id", "name", "slug", "state", "updated_at", "editorial_reviewed_at")
        read_only_fields = fields


class ManagedEntitySerializer(ManagedEntityListSerializer):
    alternative_names = VerifiedAlternativeNamesField(read_only=True)
    book_ids = serializers.SerializerMethodField()
    selected_books = serializers.SerializerMethodField()

    def get_book_ids(self, entity) -> list[str]:
        return [str(link.book_id) for link in getattr(entity, "ordered_books", [])]

    @extend_schema_field(CatalogReferenceSerializer(many=True))
    def get_selected_books(self, entity):
        return [
            {"id": str(link.book_id), "name": link.book.title}
            for link in getattr(entity, "ordered_books", [])
        ]

    class Meta:
        model = Contributor
        fields = (
            "id",
            "name",
            "slug",
            "state",
            "book_ids",
            "selected_books",
            "updated_at",
            *EDITORIAL_DETAIL_FIELDS,
        )
        read_only_fields = fields


class ManagedEntityCollectionSerializer(serializers.Serializer):
    entries = ManagedEntityListSerializer(many=True)
    pagination = AdminPaginationSerializer()


class ManagedEntityParametersSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=ContributorRole.choices, allow_blank=True, default=""
    )
    page = serializers.IntegerField(min_value=1, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)
    q = serializers.CharField(max_length=120, default="", allow_blank=True)


class EntityUpdateSerializer(BookEditorialUpdateSerializer):
    name = serializers.CharField(max_length=255, required=False)
    book_ids = serializers.ListField(
        child=serializers.UUIDField(), max_length=100, required=False
    )

    validate_name = BookEditorialUpdateSerializer.validate_title

    def validate_book_ids(self, values):
        if len(set(values)) != len(values):
            raise serializers.ValidationError("Select each book only once.")
        return values

    class Meta:
        model = Contributor
        fields = ("expected_updated_at", "name", "book_ids", *EDITORIAL_FIELDS)
        extra_kwargs: ClassVar[dict] = {}


class EntityCreateSerializer(EntityUpdateSerializer):
    operation_id = serializers.UUIDField()
    name = serializers.CharField(max_length=255)

    class Meta(EntityUpdateSerializer.Meta):
        fields = ("operation_id", "name", "book_ids", *EDITORIAL_FIELDS)

    def validate(self, attributes):
        reject_unknown_fields(self)
        return attributes


class EntityCommandSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    action = serializers.ChoiceField(choices=["review", "publish", "withdraw"])

    def validate(self, attributes):
        reject_unknown_fields(self)
        return attributes


class CatalogReferenceParametersSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=(*ENTITY_KINDS, "books"))
    q = serializers.CharField(max_length=120, default="", allow_blank=True)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=24)


class CatalogReferenceCollectionSerializer(serializers.Serializer):
    entries = CatalogReferenceSerializer(many=True)
    has_more = serializers.BooleanField()
