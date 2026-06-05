from django.conf import settings
from rest_framework import serializers
import email.utils

from apps.accounts.models import User

PASSWORD_MIN_LENGTH_MESSAGE = "Ensure this field has at least 12 characters."
PASSWORD_MIN_LENGTH_ERROR_MESSAGES = {
    "min_length": PASSWORD_MIN_LENGTH_MESSAGE
}


class UserSerializer(serializers.ModelSerializer):
    totp_enabled = serializers.BooleanField(source="has_totp_enabled", read_only=True)
    totp_required = serializers.BooleanField(read_only=True)
    totp_setup_required = serializers.BooleanField(source="requires_totp_setup", read_only=True)
    capabilities = serializers.ListField(source="capability_scopes", child=serializers.CharField(), read_only=True)
    profile_image_url = serializers.SerializerMethodField()
    kindle_emails = serializers.ListField(child=serializers.EmailField(), read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "profile_image_url",
            "is_active",
            "is_staff",
            "is_superuser",
            "totp_enabled",
            "totp_required",
            "totp_setup_required",
            "capabilities",
            "kindle_emails",
        ]

    def get_profile_image_url(self, obj):
        if not obj.profile_image:
            return ""
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(obj.profile_image.url)
        return obj.profile_image.url


class SessionSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = UserSerializer(allow_null=True)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=12,
        error_messages=PASSWORD_MIN_LENGTH_ERROR_MESSAGES,
    )

    class Meta:
        model = User
        fields = ["email", "full_name", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class ManagedUserSerializer(UserSerializer):
    grant_count = serializers.SerializerMethodField()
    global_scopes = serializers.ListField(source="global_grant_scopes", child=serializers.CharField(), read_only=True)
    can_resend_setup_email = serializers.BooleanField(read_only=True)

    class Meta(UserSerializer.Meta):
        # Exclude "capabilities" (capability_scopes) — it triggers an N+1 DB query
        # per user and is not displayed in the admin users table.
        fields = [f for f in UserSerializer.Meta.fields if f != "capabilities"] + [
            "grant_count",
            "global_scopes",
            "can_resend_setup_email",
        ]

    def get_grant_count(self, obj):
        if hasattr(obj, "grant_count_value"):
            return obj.grant_count_value
        return obj.permission_grants.count()


class ProfileSerializer(UserSerializer):
    kindle_sender_email = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            "kindle_sender_email",
        ]

    def get_kindle_sender_email(self, _obj):
        raw_email = (
            getattr(settings, "ACCOUNT_INVITE_FROM_EMAIL", "")
            or getattr(settings, "DEFAULT_FROM_EMAIL", "")
            or ""
        )
        return email.utils.parseaddr(raw_email)[1]
