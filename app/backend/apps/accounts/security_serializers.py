from rest_framework import serializers


class ReauthenticationSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        max_length=4096, trim_whitespace=False, write_only=True
    )


class SecurityTokenSerializer(serializers.Serializer):
    token = serializers.RegexField(r"^[0-9]{6}(?:[0-9]{2})?$", write_only=True)


class DisableTOTPSerializer(ReauthenticationSerializer, SecurityTokenSerializer):
    pass
