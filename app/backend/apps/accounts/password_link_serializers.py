from rest_framework import serializers

from apps.common.validation import reject_unknown_fields


class PasswordLinkSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=256)
    token = serializers.CharField(max_length=256)

    def validate(self, attrs):
        reject_unknown_fields(self)
        return attrs


class PasswordLinkInspectionSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=("setup", "reset"))
    totp_setup_required = serializers.BooleanField()


class PasswordLinkConfirmationSerializer(PasswordLinkSerializer):
    new_password = serializers.CharField(
        min_length=12, max_length=4096, trim_whitespace=False, write_only=True
    )
    confirm_new_password = serializers.CharField(
        min_length=12, max_length=4096, trim_whitespace=False, write_only=True
    )

    def validate(self, attrs):
        super().validate(attrs)
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "The passwords do not match."}
            )
        return attrs


class PasswordLinkResultSerializer(serializers.Serializer):
    next_step = serializers.ChoiceField(choices=("login", "totp_setup"))
