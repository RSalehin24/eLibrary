from ..seed_e2e_data_config import (
    BOOK_DEFINITIONS,
    E2E_SOURCE_PREFIX,
    FAILED_LOG_MESSAGE,
    PROCESSING_SUBMISSION_TITLES,
    SUBMISSION_TITLES,
    Book,
    JobStatus,
    ProcessingLog,
    ResolutionStatus,
    SubmissionOrigin,
    SubmissionStatus,
    User,
)


def create_submissions(self, admin: User, books: dict[str, Book]):
    alpha = self.create_submission_record(
        submitter=admin,
        title=SUBMISSION_TITLES[0],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.READY,
        linked_book=books["detail"],
        resolved_url=f"{E2E_SOURCE_PREFIX}alpha-submission/",
        resolution_confidence=0.97,
    )
    beta = self.create_submission_record(
        submitter=admin,
        title=SUBMISSION_TITLES[1],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.QUEUED,
        linked_book=books["home_primary"],
        resolved_url=f"{E2E_SOURCE_PREFIX}beta-submission/",
        resolution_confidence=0.91,
    )
    self.create_processing_job_record(
        submission=alpha,
        book=books["detail"],
        status=JobStatus.SUCCEEDED,
        queue_name="default",
    )
    self.create_processing_job_record(
        submission=beta,
        book=books["home_primary"],
        status=JobStatus.QUEUED,
        queue_name="default",
    )

    self.create_submission_record(
        submitter=admin,
        title=PROCESSING_SUBMISSION_TITLES["user_pending"],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.PENDING_RESOLUTION,
        resolution_status=ResolutionStatus.UNRESOLVED,
        resolution_confidence=0.0,
        resolved_url="",
    )

    user_processing = self.create_submission_record(
        submitter=admin,
        title=PROCESSING_SUBMISSION_TITLES["user_processing"],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.PROCESSING,
        linked_book=books["home_secondary"],
        resolved_url=BOOK_DEFINITIONS["home_secondary"].source_url,
    )
    self.create_processing_job_record(
        submission=user_processing,
        book=books["home_secondary"],
        status=JobStatus.PROCESSING,
        queue_name="celery",
        task_id="seed-user-processing",
    )

    user_stopped = self.create_submission_record(
        submitter=admin,
        title=PROCESSING_SUBMISSION_TITLES["user_stopped"],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.CANCELLED,
        resolved_url=BOOK_DEFINITIONS["detail"].source_url,
        error_message="Stopped by user.",
    )
    self.create_processing_job_record(
        submission=user_stopped,
        status=JobStatus.CANCELLED,
        last_error="Stopped by user.",
    )

    user_deleted = self.create_submission_record(
        submitter=admin,
        title=PROCESSING_SUBMISSION_TITLES["user_deleted"],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.DELETED,
        resolved_url=BOOK_DEFINITIONS["preview"].source_url,
    )
    self.create_processing_job_record(
        submission=user_deleted,
        status=JobStatus.CANCELLED,
        last_error="Deleted by user.",
    )

    user_failed = self.create_submission_record(
        submitter=admin,
        title=PROCESSING_SUBMISSION_TITLES["user_failed"],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.FAILED,
        error_message="Seeded failure for live-browser coverage.",
    )
    failed_job = self.create_processing_job_record(
        submission=user_failed,
        status=JobStatus.FAILED,
        last_error="Seeded failure for live-browser coverage.",
    )
    ProcessingLog.objects.create(
        job=failed_job,
        level="error",
        message=FAILED_LOG_MESSAGE,
        details={"seed": "e2e"},
    )

    self.create_automation_submissions(admin, books)
    self.create_curation_submissions(admin, books)
