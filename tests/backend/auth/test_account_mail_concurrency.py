import pytest
from apps.accounts.link_mail.requests import (
    request_invitation,
    request_invitation_resend,
    request_password_reset,
)
from apps.accounts.models import User
from apps.processing.job_models import BackgroundJob

from .account_mail_fixtures import invite_values
from .managed_access_fixtures import create_account_pair
from .test_managed_access_concurrency import concurrent_calls

pytestmark = pytest.mark.django_db(transaction=True)


def test_concurrent_identical_invitations_create_one_account_job_and_dispatch():
    actor, _ = create_account_pair("invitation-race")
    values = invite_values()
    results = concurrent_calls(request_invitation, [(actor, values)] * 2)
    assert results[0].pk == results[1].pk
    assert User.objects.filter(email=values["email"].lower()).count() == 1
    assert BackgroundJob.objects.get().dispatches.count() == 1


def test_concurrent_resend_revisions_accept_one_request():
    actor, _ = create_account_pair("resend-race")
    job = request_invitation(actor, invite_values())
    first, second = invite_values(), invite_values()
    args = [
        (
            actor,
            job.account_id,
            {
                "operation_id": values["operation_id"],
                "expected_updated_at": job.account.updated_at.isoformat(),
            },
        )
        for values in [first, second]
    ]
    assert concurrent_calls(request_invitation_resend, args).count("conflict") == 1
    assert BackgroundJob.objects.count() == 2


def test_concurrent_reset_requests_share_one_cooldown():
    target = User.objects.create_user(
        email="reset-race@library.test", password="previous-password"
    )
    concurrent_calls(request_password_reset, [(target.email,)] * 2)
    target.refresh_from_db()
    assert target.password_setup_nonce == 1 and BackgroundJob.objects.count() == 1
