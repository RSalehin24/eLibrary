from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, GeneratedAsset, MetadataReview
from apps.processing.job_models import (
    BackgroundJob,
    JobAttempt,
    JobDispatch,
)
from apps.processing.jobs.attempts import claim_attempt
from apps.processing.jobs.commands import JobConflict, enqueue_job
from apps.processing.jobs.dispatches import claim_dispatches
from django.db import close_old_connections, connections, transaction

pytestmark = pytest.mark.django_db(transaction=True)


def invoke_at_barrier(operation, argument, barrier):
    close_old_connections()
    try:
        barrier.wait(timeout=10)
        try:
            return operation(argument)
        except JobConflict:
            return "conflict"
    finally:
        connections.close_all()


def concurrent_calls(operation, arguments):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(invoke_at_barrier, operation, argument, barrier)
            for argument in arguments
        ]
        return [future.result(timeout=15) for future in futures]


def test_duplicate_concurrent_commands_persist_one_job_and_one_dispatch(command):
    jobs = concurrent_calls(enqueue_job, [command, command])
    assert jobs[0].pk == jobs[1].pk
    assert BackgroundJob.objects.count() == JobDispatch.objects.count() == 1


def test_colliding_commands_from_different_accounts_return_a_conflict(command):
    other = User.objects.create_user(email="other-job-race@library.test")
    book = Book.objects.create(title="অন্য কাজের বই")
    asset = GeneratedAsset.objects.create(book=book, asset_type="epub", status="ready")
    alternate = replace(command, actor=other, asset=asset)
    results = concurrent_calls(enqueue_job, [command, alternate])
    assert sum(result == "conflict" for result in results) == 1
    assert BackgroundJob.objects.count() == JobDispatch.objects.count() == 1


def test_duplicate_concurrent_worker_deliveries_claim_one_attempt(command):
    job = enqueue_job(command)
    identifier = job.dispatches.get().pk
    claims = concurrent_calls(claim_attempt, [identifier, identifier])
    assert sum(claim is not None for claim in claims) == 1
    assert JobAttempt.objects.count() == 1


def test_dispatchers_cannot_lease_the_same_records(command):
    enqueue_job(command)
    enqueue_job(replace(command, identifier=uuid4()))
    leases = concurrent_calls(claim_dispatches, [50, 50])
    identifiers = [lease.identifier for group in leases for lease in group]
    assert len(identifiers) == len(set(identifiers)) == 2


def record_related_review(command):
    close_old_connections()
    try:
        return MetadataReview.objects.create(
            book=command.asset.book, requested_by=command.actor
        ).pk
    finally:
        connections.close_all()


def test_command_serialization_does_not_block_an_independent_foreign_key_writer(
    command,
):
    with ThreadPoolExecutor(max_workers=1) as executor, transaction.atomic():
        enqueue_job(command)
        future = executor.submit(record_related_review, command)
        assert future.result(timeout=5)
