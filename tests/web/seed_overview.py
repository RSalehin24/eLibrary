from uuid import uuid4


def create_overview_fixture(actor, access_manager, preparation):
    from apps.accounts.link_mail.requests import request_invitation
    from apps.processing.job_models import BackgroundJob
    from django.utils import timezone

    prepared = BackgroundJob.objects.get(pk=preparation["id"])
    issue = BackgroundJob.objects.create(
        requested_by=actor,
        book=prepared.book,
        asset=prepared.asset,
        kind="prepare_epub",
        state="failed",
        available_at=timezone.now(),
        finished_at=timezone.now(),
        error_code="fixture_failure",
    )
    mail = request_invitation(
        access_manager,
        {
            "operation_id": str(uuid4()),
            "email": f"foundation-overview-{uuid4().hex}@example.test",
        },
    )
    mail.state = "needs_attention"
    mail.error_code = "mail_acceptance_unknown"
    mail.finished_at = timezone.now()
    mail.save()
    return {"processing_issue": str(issue.pk), "mail_issue": str(mail.pk)}
