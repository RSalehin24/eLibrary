from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer


class HealthSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok"])


class LivenessView(VersionedAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(operation_id="service_liveness", responses={200: HealthSerializer})
    def get(self, request):
        return Response({"status": "ok"})


class ReadinessView(LivenessView):
    @extend_schema(
        operation_id="service_readiness",
        responses={200: HealthSerializer, 503: APIErrorSerializer},
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            return Response(
                {
                    "code": "service_unavailable",
                    "detail": "The service is temporarily unavailable.",
                    "field_errors": {},
                },
                status=503,
            )
        return Response({"status": "ok"})
