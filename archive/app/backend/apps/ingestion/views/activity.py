from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ingestion.services.activity import get_processing_activity_snapshot


class ProcessingActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_processing_activity_snapshot(request.user))


__all__ = ["ProcessingActivityView"]
