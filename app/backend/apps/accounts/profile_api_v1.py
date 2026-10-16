from django.contrib.auth import update_session_auth_hash
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.profile_serializers import (
    AccountProfileSerializer,
    AccountProfileUpdateSerializer,
)
from apps.accounts.profile_services import update_account_profile
from apps.common.api import VersionedAPIView


class AccountProfileView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)

    @extend_schema(
        operation_id="account_profile", responses={200: AccountProfileSerializer}
    )
    def get(self, request):
        return Response(
            AccountProfileSerializer(request.user, context={"request": request}).data
        )

    @extend_schema(
        operation_id="account_profile_update",
        request=AccountProfileUpdateSerializer,
        responses={200: AccountProfileSerializer},
    )
    def patch(self, request):
        user, password_changed = update_account_profile(request.user, request.data)
        if password_changed:
            update_session_auth_hash(request, user)
        return Response(
            AccountProfileSerializer(user, context={"request": request}).data
        )
