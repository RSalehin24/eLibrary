from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.workspace_serializers import (
    WorkspaceSessionSerializer,
    WorkspaceUserSerializer,
)
from apps.accounts.workspaces import available_workspaces
from apps.common.api import VersionedAPIView


class WorkspaceSessionView(VersionedAPIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="workspace_session", responses=WorkspaceSessionSerializer
    )
    def get(self, request):
        user = request.user
        return Response(
            {
                "authenticated": user.is_authenticated,
                "user": WorkspaceUserSerializer(user, context={"request": request}).data
                if user.is_authenticated
                else None,
                "workspaces": available_workspaces(user),
                "csrf_token": get_token(request),
            }
        )
