from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import SavedFilter
from apps.common.serializers import SavedFilterSerializer


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "environment": settings.APP_ENV,
                "service": "bangla-library-backend",
            }
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class SavedFilterListCreateView(generics.ListCreateAPIView):
    serializer_class = SavedFilterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = SavedFilter.objects.filter(owner=self.request.user)
        target = self.request.query_params.get("target", "").strip()
        if target:
            queryset = queryset.filter(target=target)
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SavedFilterDetailView(generics.DestroyAPIView):
    serializer_class = SavedFilterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedFilter.objects.filter(owner=self.request.user)

# Create your views here.
