from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.management_access.api import paginated_response
from apps.accounts.management_access.policy import (
    AccessConflict,
    require_editable_account,
    require_revision,
)
from apps.accounts.management_access.queries import managed_account
from apps.accounts.management_access.serializers import AccessListParametersSerializer
from apps.accounts.management_access.services import locked_accounts
from apps.accounts.password_link_api_v1 import require_anonymous_link_request
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.permissions import CanManageAccess
from apps.common.throttles import PasswordResetRateThrottle
from apps.processing.job_serializers import (
    JobControlSerializer,
    OperationAcceptedSerializer,
)
from apps.processing.jobs.commands import JobConflict
from apps.processing.jobs.controls import request_stop, resume_job

from .queries import invitation_jobs
from .requests import (
    request_invitation,
    request_invitation_resend,
    request_password_reset,
)
from .serializers import (
    AccountMailCollectionSerializer,
    AccountMailOperationSerializer,
    InvitationSerializer,
    PasswordResetAcceptedSerializer,
    PasswordResetRequestSerializer,
    ResendInvitationSerializer,
)

MAIL_RESPONSES = {
    202: OperationAcceptedSerializer,
    400: APIErrorSerializer,
    403: APIErrorSerializer,
    404: APIErrorSerializer,
    409: APIErrorSerializer,
}
RESET_ACCEPTED = (
    "If this address has an eligible account, a password reset email will be sent."
)


def mail_accepted(job):
    status_url = reverse("api_v1:account-mail-operation", kwargs={"identifier": job.pk})
    return Response({"operation_id": str(job.pk), "status_url": status_url}, status=202)


@transaction.atomic
def control_invitation(actor, identifier, values):
    snapshot = get_object_or_404(invitation_jobs(), pk=identifier)
    locked_accounts(actor, snapshot.account_id)
    job = get_object_or_404(invitation_jobs().select_for_update(), pk=identifier)
    require_revision(job, values["expected_updated_at"])
    try:
        return (
            resume_job(job.pk)
            if values["action"] == "resume"
            else request_stop(job.pk, values["action"])
        )
    except JobConflict as error:
        raise AccessConflict(str(error)) from error


class ManagedInvitationView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageAccess)

    @extend_schema(
        operation_id="managed_invitation_create",
        request=InvitationSerializer,
        responses=MAIL_RESPONSES,
    )
    def post(self, request):
        return mail_accepted(request_invitation(request.user, request.data))


class ManagedInvitationResendView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageAccess)

    @extend_schema(
        operation_id="managed_invitation_resend",
        request=ResendInvitationSerializer,
        responses=MAIL_RESPONSES,
    )
    def post(self, request, identifier):
        return mail_accepted(
            request_invitation_resend(request.user, identifier, request.data)
        )


class AccountMailOperationsView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageAccess)

    @extend_schema(
        operation_id="account_mail_operations",
        parameters=[AccessListParametersSerializer],
        responses={
            200: AccountMailCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, identifier):
        parameters = AccessListParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        target = managed_account(identifier)
        require_editable_account(request.user, target)
        return paginated_response(
            invitation_jobs().filter(account=target),
            AccountMailOperationSerializer,
            request,
        )


class AccountMailOperationView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageAccess)

    @extend_schema(
        operation_id="account_mail_operation",
        responses={
            200: AccountMailOperationSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, identifier):
        job = get_object_or_404(
            invitation_jobs().select_related("account"), pk=identifier
        )
        require_editable_account(request.user, job.account)
        return Response(AccountMailOperationSerializer(job).data)

    @extend_schema(
        operation_id="account_mail_control",
        request=JobControlSerializer,
        responses=MAIL_RESPONSES,
    )
    def post(self, request, identifier):
        parameters = JobControlSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        return mail_accepted(
            control_invitation(request.user, identifier, parameters.validated_data)
        )


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestView(VersionedAPIView):
    permission_classes = (AllowAny,)
    throttle_classes = (PasswordResetRateThrottle,)

    @extend_schema(
        operation_id="password_reset_request",
        request=PasswordResetRequestSerializer,
        responses={
            202: PasswordResetAcceptedSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            429: APIErrorSerializer,
            503: APIErrorSerializer,
        },
    )
    def post(self, request):
        require_anonymous_link_request(request)
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data["email"])
        return Response({"detail": RESET_ACCEPTED}, status=202)
