from typing import ClassVar

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.kindle import MAX_KINDLE_RECIPIENTS
from apps.accounts.serializers.base import ProfileSerializer
from apps.accounts.serializers.profile import ProfileUpdateSerializer
from apps.common.permissions import user_can_configure_kindle


class AccountProfileSerializer(ProfileSerializer):
    can_configure_kindle = serializers.SerializerMethodField()
    updated_at = serializers.DateTimeField(read_only=True)

    def get_profile_image_url(self, user) -> str:
        from apps.accounts.profile_images import profile_image_url

        return profile_image_url(user)

    class Meta(ProfileSerializer.Meta):
        fields: ClassVar = [
            *ProfileSerializer.Meta.fields,
            "can_configure_kindle",
            "updated_at",
        ]

    @extend_schema_field(serializers.BooleanField())
    def get_can_configure_kindle(self, user):
        return user_can_configure_kindle(user)


class AccountProfileUpdateSerializer(ProfileUpdateSerializer):
    expected_updated_at = serializers.DateTimeField()
    new_password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=12,
        max_length=4096,
        trim_whitespace=False,
    )
    kindle_emails = serializers.ListField(
        child=serializers.EmailField(), max_length=MAX_KINDLE_RECIPIENTS, required=False
    )

    class Meta(ProfileUpdateSerializer.Meta):
        fields: ClassVar = [
            "expected_updated_at",
            "full_name",
            "current_password",
            "new_password",
            "confirm_new_password",
            "kindle_emails",
        ]

    def can_configure_kindle(self):
        return user_can_configure_kindle(self.instance)

    def update(self, instance, validated_data):
        validated_data.pop("expected_updated_at")
        return super().update(instance, validated_data)
