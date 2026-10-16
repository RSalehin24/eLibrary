from apps.processing.job_models import BackgroundJobKind


def count_failed_attempts(job):
    attempts = job.attempts.exclude(error_code="")
    if job.kind == BackgroundJobKind.PROCESS_SOURCE:
        attempts = attempts.filter(number__gt=job.input.get("retry_after_attempt", 0))
    return attempts.count()
