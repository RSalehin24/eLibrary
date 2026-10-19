from apps.processing.job_models import BackgroundJobKind

from .source_recovery import SOURCE_AVAILABILITY_ERRORS


def count_failed_attempts(job):
    attempts = job.attempts.exclude(error_code="")
    if job.kind == BackgroundJobKind.PROCESS_SOURCE:
        attempts = attempts.filter(
            number__gt=job.input.get("retry_after_attempt", 0)
        ).exclude(error_code__in=[*SOURCE_AVAILABILITY_ERRORS, "source_record_changed"])
    return attempts.count()
