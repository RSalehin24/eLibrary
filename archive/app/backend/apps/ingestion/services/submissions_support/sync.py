def primary_source_url_for_book(book):
    source = book.source_urls.order_by("-is_primary", "-created_at").first()
    return source.normalized_source_url if source else ""


def root_submission(submission):
    return submission.canonical_submission or submission


def build_retry_payload(raw_payload, actor, previous_status, previous_error_message, reset_keys):
    next_payload = dict(raw_payload or {})
    for key in (
        "requeued",
        "requeued_at",
        "requeue_requested_by",
        "requeue_reason",
    ):
        next_payload.pop(key, None)
    for key in reset_keys:
        next_payload.pop(key, None)
    return next_payload


def sync_submission_from_canonical(
    submission,
    canonical_submission,
    *,
    ensure_preview_session_callback,
    root_submission_callback,
    shared_payload_keys,
    submission_status,
):
    canonical_submission = root_submission_callback(canonical_submission)
    if submission.pk == canonical_submission.pk:
        return submission

    update_fields = []
    field_names = (
        "resolved_url",
        "resolution_status",
        "resolution_confidence",
        "status",
        "review_state",
        "linked_book",
        "duplicate_of_book",
        "error_message",
    )
    for field_name in field_names:
        canonical_value = getattr(canonical_submission, field_name)
        if getattr(submission, field_name) != canonical_value:
            setattr(submission, field_name, canonical_value)
            update_fields.append(field_name)

    if submission.canonical_submission_id != canonical_submission.id:
        submission.canonical_submission = canonical_submission
        update_fields.append("canonical_submission")

    next_payload = {
        **submission.raw_payload,
        "deduplicated": True,
        "canonical_submission_id": str(canonical_submission.id),
    }
    for key in shared_payload_keys:
        if key in canonical_submission.raw_payload:
            next_payload[key] = canonical_submission.raw_payload[key]
    if submission.raw_payload != next_payload:
        submission.raw_payload = next_payload
        update_fields.append("raw_payload")

    if update_fields:
        submission.save(update_fields=[*update_fields, "updated_at"])

    if (
        submission.status == submission_status.READY
        and submission.linked_book_id
        and submission.submitter_id
    ):
        ensure_preview_session_callback(
            submission.submitter,
            submission.linked_book,
            submission=submission,
        )

    return submission


def sync_deduplicated_submissions(
    submission,
    *,
    root_submission_callback,
    sync_submission_from_canonical_callback,
):
    submission = root_submission_callback(submission)
    for dependent_submission in submission.deduplicated_submissions.select_related(
        "submitter",
        "linked_book",
    ):
        sync_submission_from_canonical_callback(dependent_submission, submission)
