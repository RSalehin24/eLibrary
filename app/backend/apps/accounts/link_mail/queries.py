from apps.processing.job_models import BackgroundJob, BackgroundJobKind


def invitation_jobs():
    return BackgroundJob.objects.filter(
        kind=BackgroundJobKind.ACCOUNT_MAIL,
        input__command__action__in=["invite", "resend"],
    )
