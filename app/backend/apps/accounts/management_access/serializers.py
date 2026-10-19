from typing import ClassVar

from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.access.models import ACCOUNT_MANAGEABLE_PERMISSION_SCOPES
from apps.access.serializers import PermissionGrantSerializer
from apps.accounts.models import User
from apps.common.api_serializers import AdminPaginationSerializer
from apps.common.validation import reject_unknown_fields

from .policy import account_is_editable


class ManagedAccountSerializer(serializers.ModelSerializer):
    has_totp_enabled = serializers.BooleanField(read_only=True)
    grant_count = serializers.IntegerField(source="grant_count_value", read_only=True)
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "totp_required",
            "has_totp_enabled",
            "email_setup_pending",
            "grant_count",
            "updated_at",
            "can_edit",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField())
    def get_can_edit(self, user):
        return account_is_editable(self.context["actor"], user)


class ManagedAccountUpdateSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    totp_required = serializers.BooleanField(required=False)

    def validate(self, attrs):
        reject_unknown_fields(self)
        return attrs


class AccessListParametersSerializer(serializers.Serializer):
    q = serializers.CharField(
        max_length=200, required=False, default="", allow_blank=True
    )
    page = serializers.IntegerField(min_value=1, required=False, default=1)
    limit = serializers.IntegerField(
        min_value=1, max_value=100, required=False, default=50
    )


class ManagedAccountParametersSerializer(AccessListParametersSerializer):
    status = serializers.ChoiceField(
        choices=("all", "active", "disabled", "setup_pending", "totp_required"),
        default="all",
    )
    sort = serializers.ChoiceField(
        choices=("name_asc", "name_desc", "email_asc", "email_desc", "status"),
        default="name_asc",
    )


class ManagedAccountCollectionSerializer(serializers.Serializer):
    entries = ManagedAccountSerializer(many=True)
    pagination = AdminPaginationSerializer()


class ManagedGrantSerializer(PermissionGrantSerializer):
    updated_at = serializers.DateTimeField(read_only=True)
    effective = serializers.SerializerMethodField()
    book_slug = serializers.CharField(source="book.slug", read_only=True, default="")
    book_title = serializers.CharField(source="book.title", read_only=True, default="")
    category_slug = serializers.CharField(
        source="category.slug", read_only=True, default=""
    )
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=""
    )
    contributor_slug = serializers.CharField(
        source="contributor.slug", read_only=True, default=""
    )
    contributor_name = serializers.CharField(
        source="contributor.name", read_only=True, default=""
    )

    class Meta(PermissionGrantSerializer.Meta):
        fields: ClassVar[list[str]] = [
            field
            for field in PermissionGrantSerializer.Meta.fields
            if field != "granted_by_email"
        ] + ["updated_at", "effective"]
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField())
    def get_effective(self, grant):
        return grant.is_active and (
            grant.expires_at is None or grant.expires_at > timezone.now()
        )


class ManagedGrantCreateSerializer(PermissionGrantSerializer):
    id = serializers.UUIDField()
    scope = serializers.ChoiceField(choices=ACCOUNT_MANAGEABLE_PERMISSION_SCOPES)
    notes = serializers.CharField(
        max_length=2000, required=False, default="", allow_blank=True
    )

    class Meta(PermissionGrantSerializer.Meta):
        fields: ClassVar[list[str]] = [
            "id",
            "book",
            "category",
            "contributor",
            "scope",
            "expires_at",
            "notes",
        ]

    def validate(self, attrs):
        reject_unknown_fields(self)
        attrs["user"] = self.context["target"]
        if attrs.get("book") is not None and attrs["book"].deleted_at is not None:
            raise serializers.ValidationError({"book": "Choose an available book."})
        return super().validate(attrs)


class ManagedGrantUpdateSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    is_active = serializers.BooleanField(required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    def validate(self, attrs):
        reject_unknown_fields(self)
        return attrs


class ManagedGrantCollectionSerializer(serializers.Serializer):
    entries = ManagedGrantSerializer(many=True)
    pagination = AdminPaginationSerializer()


class AccessReferenceParametersSerializer(AccessListParametersSerializer):
    kind = serializers.ChoiceField(choices=("book", "category", "author"))


class AccessReferenceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()


class AccessReferenceCollectionSerializer(serializers.Serializer):
    entries = AccessReferenceSerializer(many=True)
    pagination = AdminPaginationSerializer()
