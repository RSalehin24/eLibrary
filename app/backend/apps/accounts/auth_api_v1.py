from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import serializers

from apps.accounts.serializers import LoginSerializer, UserSerializer
from apps.accounts.view_modules.auth_and_password_views import LoginView, LogoutView
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer


class WorkspaceLoginSerializer(LoginSerializer):
    password = serializers.CharField(
        write_only=True, max_length=4096, trim_whitespace=False
    )


@method_decorator(csrf_protect, name="dispatch")
class WorkspaceLoginView(LoginView, VersionedAPIView):
    serializer_class = WorkspaceLoginSerializer

    @extend_schema(
        operation_id="workspace_login",
        request=WorkspaceLoginSerializer,
        responses={
            200: UserSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            503: APIErrorSerializer,
        },
    )
    def post(self, request):
        return super().post(request)


class WorkspaceLogoutView(LogoutView, VersionedAPIView):
    @extend_schema(operation_id="workspace_logout", request=None, responses={204: None})
    def post(self, request):
        return super().post(request)
