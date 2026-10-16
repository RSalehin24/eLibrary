"""Request pipeline tick."""

from ..models import BookCreationRequest, BookCreationRequestState
from . import checkpoint_and_runtime_adapters as _checkpoints
from . import maintenance_and_request_actions as _maintenance
from . import request_processing_persistence as _persistence
from . import request_processing_pipeline as _pipeline
from . import request_queue_runtime as _request_queue


def advance_pipeline_once():
    advanced = 0
    advanced += len(_maintenance.mark_stale_processing_requests())

    queued_request = (
        BookCreationRequest.objects.filter(state=BookCreationRequestState.QUEUED)
        .order_by("created_at", "id")
        .first()
    )
    if queued_request:
        if _checkpoints.should_run_processing_jobs_inline():
            _pipeline._transition_request_state(
                queued_request.id,
                BookCreationRequestState.QUEUED,
                BookCreationRequestState.PROCESSING,
            )
            advanced += 1
        elif _checkpoints.should_enqueue_processing_work():
            workers_available = _checkpoints.processing_workers_available()
            if (
                not _persistence._request_dispatch_pending(queued_request)
                or not workers_available
            ):
                if (
                    not workers_available
                    or not _request_queue.enqueue_request_processing(queued_request)
                ):
                    _pipeline.kickoff_request_processing(queued_request.id)
                advanced += 1
        else:
            _pipeline._transition_request_state(
                queued_request.id,
                BookCreationRequestState.QUEUED,
                BookCreationRequestState.PROCESSING,
            )
            advanced += 1

    processing_request = (
        BookCreationRequest.objects.filter(state=BookCreationRequestState.PROCESSING)
        .order_by("created_at", "id")
        .first()
    )
    if processing_request and (
        _checkpoints.should_run_processing_jobs_inline()
        or _checkpoints.should_manually_advance_processing_work()
    ):
        _pipeline._run_processing_request(processing_request)
        advanced += 1

    initial_request = (
        BookCreationRequest.objects.filter(state=BookCreationRequestState.INITIAL)
        .order_by("created_at", "id")
        .first()
    )
    if initial_request:
        _pipeline._transition_request_state(
            initial_request.id,
            BookCreationRequestState.INITIAL,
            BookCreationRequestState.QUEUED,
        )
        advanced += 1

    if advanced == 0:
        _maintenance.repair_self_linked_duplicate_requests()
    return advanced
