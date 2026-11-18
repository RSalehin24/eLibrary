def create_submissions(self, admin: User, books: dict[str, Book]):
    alpha = self.create_submission_record(
        submitter=admin,
        title=SUBMISSION_TITLES[0],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.READY,
        review_state=ReviewState.APPROVED,
        linked_book=books["detail"],
        resolved_url=f"{E2E_SOURCE_PREFIX}alpha-submission/",
        resolution_confidence=0.97,
    )
    beta = self.create_submission_record(
        submitter=admin,
        title=SUBMISSION_TITLES[1],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.QUEUED,
        review_state=ReviewState.PENDING,
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
        review_state=ReviewState.PENDING,
        resolution_status=ResolutionStatus.UNRESOLVED,
        resolution_confidence=0.0,
        resolved_url="",
    )

    user_processing = self.create_submission_record(
        submitter=admin,
        title=PROCESSING_SUBMISSION_TITLES["user_processing"],
        origin=SubmissionOrigin.USER,
        status=SubmissionStatus.PROCESSING,
        review_state=ReviewState.PENDING,
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
        review_state=ReviewState.PENDING,
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
        review_state=ReviewState.PENDING,
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
        review_state=ReviewState.NEEDS_REVIEW,
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

    for title, status, review_state, book_key, resolved_book_key, job_status, task_id in (
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

    for title, status, review_state, book_key, resolved_book_key, job_status, task_id in (
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
            last_error="Stopped by user."
            if job_status == JobStatus.CANCELLED
            else "",
        )
