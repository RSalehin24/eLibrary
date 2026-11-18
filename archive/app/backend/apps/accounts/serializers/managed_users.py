from rest_framework import serializers

from apps.accounts.models import User

from .base import PASSWORD_MIN_LENGTH_ERROR_MESSAGES
from .support import MANAGEABLE_PERMISSION_SCOPES, create_managed_user, sync_global_grants


class ManagedUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=12,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        error_messages=PASSWORD_MIN_LENGTH_ERROR_MESSAGES,
    )
    is_active = serializers.BooleanField(default=True)
    totp_required = serializers.BooleanField(default=False)
    send_invite_email = serializers.BooleanField(default=True, required=False, write_only=True)
    global_scopes = serializers.ListField(
        child=serializers.ChoiceField(choices=[scope.value for scope in MANAGEABLE_PERMISSION_SCOPES]),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = User
        fields = ["email", "full_name", "password", "is_active", "totp_required", "send_invite_email", "global_scopes"]

    def validate_global_scopes(self, value):
        if not value:
            raise serializers.ValidationError("Select at least one account permission.")
        if "read:once" in value and "read:durable" in value:
            raise serializers.ValidationError("Read Once and Durable Read permissions are mutually exclusive.")
        return value

    def validate(self, attrs):
        password = (attrs.get("password") or "").strip()
        send_invite_email = attrs.get("send_invite_email", True)
        if not password and not send_invite_email:
            raise serializers.ValidationError({"password": "Set a password or send an invite email."})
        if send_invite_email and not attrs.get("is_active", True):
            raise serializers.ValidationError({"is_active": "Activate the account before sending an invite email."})
        return attrs

    def create(self, validated_data):
        return create_managed_user(validated_data, request=self.context["request"])


class ManagedUserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=12,
        required=False,
        allow_blank=False,
        error_messages=PASSWORD_MIN_LENGTH_ERROR_MESSAGES,
    )
    global_scopes = serializers.ListField(
        child=serializers.ChoiceField(choices=[scope.value for scope in MANAGEABLE_PERMISSION_SCOPES]),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = User
        fields = ["email", "full_name", "is_active", "password", "totp_required", "global_scopes"]

    def validate_global_scopes(self, value):
        if value == []:
            raise serializers.ValidationError("Select at least one account permission.")
        if "read:once" in value and "read:durable" in value:
            raise serializers.ValidationError("Read Once and Durable Read permissions are mutually exclusive.")
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop("password", "")
        global_scopes = validated_data.pop("global_scopes", None)
        update_fields = []
        for field, value in validated_data.items():
            setattr(instance, field, value)
            update_fields.append(field)
        if password:
            instance.set_password(password)
            update_fields.append("password")
        if (
            instance.email_setup_pending
            and instance.has_usable_password()
            and not instance.requires_totp_setup
        ):
            instance.email_setup_pending = False
            update_fields.append("email_setup_pending")
        instance.save(update_fields=sorted(set(update_fields)) or None)
        if global_scopes is not None:
            sync_global_grants(instance, global_scopes, actor=self.context["request"].user)
        return instance
