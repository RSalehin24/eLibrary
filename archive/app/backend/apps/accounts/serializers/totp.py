from base64 import b32encode

from rest_framework import serializers

from .support import build_qr_svg


class TOTPStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    pending_setup = serializers.BooleanField()
    required = serializers.BooleanField()
    setup_required = serializers.BooleanField()


class TOTPSetupSerializer(serializers.Serializer):
    provisioning_uri = serializers.CharField()
    secret = serializers.CharField()
    qr_svg = serializers.CharField()

    @staticmethod
    def from_device(device):
        provisioning_uri = device.config_url
        secret = b32encode(device.bin_key).decode("utf-8").rstrip("=")
        return {
            "provisioning_uri": provisioning_uri,
            "secret": secret,
            "qr_svg": build_qr_svg(provisioning_uri),
        }


class TOTPConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
