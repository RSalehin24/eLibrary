from typing import ClassVar

from rest_framework import serializers

from apps.ingestion.models import ProcessingLog


class ProcessingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingLog
        fields: ClassVar = ["id", "level", "message", "details", "created_at"]


__all__ = ["ProcessingLogSerializer"]
