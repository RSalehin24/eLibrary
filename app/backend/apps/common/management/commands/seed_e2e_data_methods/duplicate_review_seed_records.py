from ..seed_e2e_data_config import (
    BOOK_DEFINITIONS,
    PROCESSING_SUBMISSION_TITLES,
    Book,
    JobStatus,
    ResolutionStatus,
    SubmissionOrigin,
    SubmissionStatus,
    User,
)


def create_automation_submissions(self, admin: User, books: dict[str, Book]):
    for (
        title,
        status,
        book_key,
        resolved_book_key,
        job_status,
        task_id,
    ) in (
        (
            PROCESSING_SUBMISSION_TITLES["automation_pending"],
            SubmissionStatus.PENDING_RESOLUTION,
            None,
            None,
            "",
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["automation_ready"],
            SubmissionStatus.READY,
            "preview",
            "preview",
            JobStatus.SUCCEEDED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["automation_processing"],
            SubmissionStatus.PROCESSING,
            "preview",
            "preview",
            JobStatus.PROCESSING,
            "seed-automation-processing",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["automation_queued"],
            SubmissionStatus.QUEUED,
            "preview",
            "preview",
            JobStatus.QUEUED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["automation_stopped"],
            SubmissionStatus.CANCELLED,
            None,
            "preview",
            JobStatus.CANCELLED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["automation_deleted"],
            SubmissionStatus.DELETED,
            None,
            "preview",
            JobStatus.CANCELLED,
            "",
        ),
    ):
        submission = self.create_submission_record(
            submitter=admin,
            title=title,
            origin=SubmissionOrigin.AUTOMATION,
            status=status,
            linked_book=books[book_key] if book_key else None,
            resolution_status=(
                ResolutionStatus.UNRESOLVED
                if status == SubmissionStatus.PENDING_RESOLUTION
                else ResolutionStatus.RESOLVED
            ),
            resolution_confidence=0.0
            if status == SubmissionStatus.PENDING_RESOLUTION
            else 0.9,
            resolved_url=""
            if status == SubmissionStatus.PENDING_RESOLUTION
            else BOOK_DEFINITIONS[resolved_book_key].source_url,
            error_message="Stopped by user."
            if status == SubmissionStatus.CANCELLED
            else "",
        )
        if job_status:
            self.create_processing_job_record(
                submission=submission,
                book=books[book_key] if book_key else None,
                status=job_status,
                queue_name="celery" if job_status == JobStatus.PROCESSING else "",
                task_id=task_id,
                last_error="Stopped by user."
                if job_status == JobStatus.CANCELLED
                else "",
            )


def create_curation_submissions(self, admin: User, books: dict[str, Book]):
    for (
        title,
        status,
        book_key,
        resolved_book_key,
        job_status,
        task_id,
    ) in (
        (
            PROCESSING_SUBMISSION_TITLES["curation_ready"],
            SubmissionStatus.READY,
            "access",
            "access",
            JobStatus.SUCCEEDED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["curation_processing"],
            SubmissionStatus.PROCESSING,
            "access",
            "access",
            JobStatus.PROCESSING,
            "seed-curation-processing",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["curation_queued"],
            SubmissionStatus.QUEUED,
            "access",
            "access",
            JobStatus.QUEUED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["curation_stopped"],
            SubmissionStatus.CANCELLED,
            None,
            "access",
            JobStatus.CANCELLED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["curation_deleted"],
            SubmissionStatus.DELETED,
            None,
            "access",
            JobStatus.CANCELLED,
            "",
        ),
    ):
        submission = self.create_submission_record(
            submitter=admin,
            title=title,
            origin=SubmissionOrigin.CURATION,
            status=status,
            linked_book=books[book_key] if book_key else None,
            resolved_url=BOOK_DEFINITIONS[resolved_book_key].source_url,
            error_message="Stopped by user."
            if status == SubmissionStatus.CANCELLED
            else "",
        )
        self.create_processing_job_record(
            submission=submission,
            book=books[book_key] if book_key else None,
            status=job_status,
            queue_name="celery" if job_status == JobStatus.PROCESSING else "",
            task_id=task_id,
            last_error="Stopped by user." if job_status == JobStatus.CANCELLED else "",
        )
