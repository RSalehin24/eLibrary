from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from apps.accounts.models import User
from apps.accounts.profile_serializers import AccountProfileUpdateSerializer


class ProfileConflict(APIException):
    status_code = 409
    default_code = "state_conflict"
    default_detail = "Your profile changed. Refresh before saving."


@transaction.atomic
def update_account_profile(user, values):
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    serializer = AccountProfileUpdateSerializer(locked_user, data=values, partial=True)
    serializer.is_valid(raise_exception=True)
    if "expected_updated_at" not in serializer.validated_data:
        raise ValidationError(
            {"expected_updated_at": "Refresh your profile before saving."}
        )
    if serializer.validated_data.get("expected_updated_at") != locked_user.updated_at:
        raise ProfileConflict()
    serializer.save()
    return locked_user, serializer.password_changed
