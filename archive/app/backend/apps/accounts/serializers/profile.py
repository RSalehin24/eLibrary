from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.access.models import PermissionScope
from apps.accounts.kindle import validate_kindle_email_address
from apps.accounts.models import User
from apps.common.permissions import user_has_scope


def normalize_kindle_emails(raw_value):
    if raw_value is None:
        return None

    if isinstance(raw_value, str):
        candidates = raw_value.replace(";", "\n").replace(",", "\n").splitlines()
    elif isinstance(raw_value, (list, tuple)):
        candidates = raw_value
    else:
        raise serializers.ValidationError(
            {"kindle_emails": "Enter one Kindle email per line."}
        )

    normalized = []
    seen = set()
    for candidate in candidates:
        email = str(candidate or "").strip().lower()
        if not email:
            continue
        try:
            email = validate_kindle_email_address(email)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"kindle_emails": list(exc.messages)}
            ) from exc
        if email in seen:
            continue
        seen.add(email)
        normalized.append(email)

    return normalized


class ProfileUpdateSerializer(serializers.ModelSerializer):
    profile_image = serializers.FileField(required=False, allow_null=True)
    remove_profile_image = serializers.BooleanField(required=False, default=False, write_only=True)
    current_password = serializers.CharField(write_only=True, required=False, allow_blank=False, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, required=False, allow_blank=False, trim_whitespace=False)
    confirm_new_password = serializers.CharField(write_only=True, required=False, allow_blank=False, trim_whitespace=False)
    kindle_emails = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
    )
    kindle_emails_text = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = User
        fields = [
            "full_name",
            "profile_image",
            "remove_profile_image",
            "current_password",
            "new_password",
            "confirm_new_password",
            "kindle_emails",
            "kindle_emails_text",
        ]

    def validate(self, attrs):
        kindle_emails_supplied = "kindle_emails" in attrs or "kindle_emails_text" in attrs
        if kindle_emails_supplied and not user_has_scope(self.instance, [PermissionScope.SEND_KINDLE]):
            raise serializers.ValidationError(
                {"kindle_emails": "You do not have the Send to Kindle permission."}
            )
        if "kindle_emails_text" in attrs:
            attrs["kindle_emails"] = normalize_kindle_emails(
                attrs.get("kindle_emails_text", "")
            )
        elif "kindle_emails" in attrs:
            attrs["kindle_emails"] = normalize_kindle_emails(
                attrs.get("kindle_emails")
            )
        elif kindle_emails_supplied:
            attrs["kindle_emails"] = []

        current_password = attrs.get("current_password", "")
        new_password = attrs.get("new_password", "")
        confirm_new_password = attrs.get("confirm_new_password", "")
        has_password_change = any([current_password, new_password, confirm_new_password])
        if not has_password_change:
            return attrs
        if not current_password:
            raise serializers.ValidationError({"current_password": "Enter your current password."})
        if not self.instance.check_password(current_password):
            raise serializers.ValidationError({"current_password": "Current password is incorrect."})
        if not new_password:
            raise serializers.ValidationError({"new_password": "Enter a new password."})
        if not confirm_new_password:
            raise serializers.ValidationError({"confirm_new_password": "Confirm your new password."})
        if new_password != confirm_new_password:
            raise serializers.ValidationError({"confirm_new_password": "The new password fields must match."})
        if self.instance.check_password(new_password):
            raise serializers.ValidationError({"new_password": "Choose a different password."})
        try:
            validate_password(new_password, self.instance)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        return attrs

    def update(self, instance, validated_data):
        remove_profile_image = validated_data.pop("remove_profile_image", False)
        profile_image = validated_data.pop("profile_image", None)
        validated_data.pop("current_password", "")
        new_password = validated_data.pop("new_password", "")
        validated_data.pop("confirm_new_password", "")
        validated_data.pop("kindle_emails_text", None)
        kindle_emails = validated_data.pop("kindle_emails", None)
        self.password_changed = False

        if remove_profile_image and instance.profile_image:
            instance.profile_image.delete(save=False)
            instance.profile_image = None
        if profile_image is not None:
            if instance.profile_image:
                instance.profile_image.delete(save=False)
            instance.profile_image = profile_image
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if kindle_emails is not None:
            instance.kindle_emails = kindle_emails
        if new_password:
            instance.set_password(new_password)
            self.password_changed = True
        instance.save()
        return instance
