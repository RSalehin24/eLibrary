from ..seed_e2e_data_config import (
    BOOK_DEFINITIONS,
    PROCESSING_SUBMISSION_TITLES,
    Book,
    DuplicateReview,
    DuplicateReviewStatus,
    JobStatus,
    ResolutionStatus,
    ReviewState,
    SubmissionOrigin,
    SubmissionStatus,
    User,
)


def create_duplicate_review(self, admin: User, books: dict[str, Book]):
    duplicate_submission = self.create_submission_record(
        submitter=admin,
        title=PROCESSING_SUBMISSION_TITLES["duplicate_review"],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.DUPLICATE,
        review_state=ReviewState.NEEDS_REVIEW,
        linked_book=None,
        resolved_url=BOOK_DEFINITIONS["preview"].source_url,
    )
    DuplicateReview.objects.create(
        submission=duplicate_submission,
        existing_book=books["home_secondary"],
        status=DuplicateReviewStatus.PENDING,
        notes="Seeded duplicate review for live-browser coverage.",
    )


def create_automation_submissions(self, admin: User, books: dict[str, Book]):
    for (
        title,
        status,
        review_state,
        book_key,
        resolved_book_key,
        job_status,
        task_id,
    ) in (
        (
            PROCESSING_SUBMISSION_TITLES["automation_pending"],
            SubmissionStatus.PENDING_RESOLUTION,
            ReviewState.PENDING,
            None,
            None,
            "",
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["automation_ready"],
            SubmissionStatus.READY,
            ReviewState.APPROVED,
            "preview",
            "preview",
            JobStatus.SUCCEEDED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["automation_processing"],
            SubmissionStatus.PROCESSING,
            ReviewState.PENDING,
            "preview",
            "preview",
            JobStatus.PROCESSING,
            "seed-automation-processing",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["automation_queued"],
            SubmissionStatus.QUEUED,
            ReviewState.PENDING,
            "preview",
            "preview",
            JobStatus.QUEUED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["automation_stopped"],
            SubmissionStatus.CANCELLED,
            ReviewState.PENDING,
            None,
            "preview",
            JobStatus.CANCELLED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["automation_deleted"],
            SubmissionStatus.DELETED,
            ReviewState.PENDING,
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
            review_state=review_state,
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
        review_state,
        book_key,
        resolved_book_key,
        job_status,
        task_id,
    ) in (
        (
            PROCESSING_SUBMISSION_TITLES["curation_ready"],
            SubmissionStatus.READY,
            ReviewState.APPROVED,
            "access",
            "access",
            JobStatus.SUCCEEDED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["curation_processing"],
            SubmissionStatus.PROCESSING,
            ReviewState.PENDING,
            "access",
            "access",
            JobStatus.PROCESSING,
            "seed-curation-processing",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["curation_queued"],
            SubmissionStatus.QUEUED,
            ReviewState.PENDING,
            "access",
            "access",
            JobStatus.QUEUED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["curation_stopped"],
            SubmissionStatus.CANCELLED,
            ReviewState.PENDING,
            None,
            "access",
            JobStatus.CANCELLED,
            "",
        ),
        (
            PROCESSING_SUBMISSION_TITLES["curation_deleted"],
            SubmissionStatus.DELETED,
            ReviewState.PENDING,
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
            review_state=review_state,
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
