from rest_framework import serializers

from apps.common.models import SavedFilter


class SavedFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedFilter
        fields = ["id", "target", "name", "params", "created_at"]
        read_only_fields = ["created_at"]
