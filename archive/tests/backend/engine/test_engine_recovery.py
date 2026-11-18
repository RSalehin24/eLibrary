"""Tests for Central Job Engine: Engine Recovery After Restart.

Verifies that the Engine can recover its state from Redis and the
database after a restart, without losing jobs or double-processing.
"""

import json
import time

import pytest

from .constants import *
from .helpers import *


class TestEngineRecovery:
    """Engine must recover state on restart."""

    def test_restart_preserves_existing_workers(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        engine.stop()
        time.sleep(0.3)

        engine.start()
        time.sleep(0.3)

        assert docker_redis_client.exists(worker.worker_key()), \
            "Worker should still be registered after engine restart"
        assert_worker_field(docker_redis_client, worker.hostname, "hostname", worker.hostname)

    def test_restart_reprocesses_pending_queue(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        job_ids = [f"recovery-queue-{i:03d}" for i in range(3)]
        for jid in job_ids:
            publish_job_request(docker_redis_client, jid)
        assert wait_for_queue_length(docker_redis_client, 2, timeout=3.0)

        # Complete all jobs so worker is idle after restart
        for jid in job_ids:
            assert wait_for_redis_hash_field_value(
                docker_redis_client, ACTIVE_JOBS, jid, worker.hostname, timeout=3.0,
            )
            worker.complete_job(jid)
            time.sleep(0.2)

        engine.stop()
        time.sleep(0.3)

        # Clear and refill queue with known set of jobs
        docker_redis_client.delete(PENDING_QUEUE)
        for jid in job_ids:
            docker_redis_client.rpush(PENDING_QUEUE, jid)
        time.sleep(0.1)

        engine.start()

        # After restart, worker is idle, one job should be assigned
        assert wait_for_queue_length(docker_redis_client, len(job_ids) - 1, timeout=5.0), \
            "Pending queue should be processed after restart"

    def test_restart_with_active_jobs_requeues_when_no_worker(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, hostname="recovery-worker@test")
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        job_id = "recovery-active-001"
        publish_job_request(docker_redis_client, job_id)
        time.sleep(0.3)
        assert_job_active(docker_redis_client, job_id, worker.hostname)

        engine.stop()
        time.sleep(0.3)

        docker_redis_client.hset(worker.worker_key(), "status", WORKER_STATUS_OFFLINE)

        engine.start()
        time.sleep(0.3)

        job_owner = docker_redis_client.hget(ACTIVE_JOBS, job_id)
        assert job_owner is None, \
            f"Job {job_id} should be removed from active after restart, got owner {job_owner}"

        assert wait_for_queue_length(docker_redis_client, 1), \
            "Job should be requeued after dead worker recovery"

    def test_restart_maps_active_jobs_to_workers(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, hostname="active-worker@test")
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        engine.stop()
        time.sleep(0.3)

        docker_redis_client.hset(ACTIVE_JOBS, "prior-active-job-001", worker.hostname)
        docker_redis_client.hset(worker.worker_key(), "current_job", "prior-active-job-001")
        docker_redis_client.hset(worker.worker_key(), "status", WORKER_STATUS_PROCESSING)

        engine.start()
        time.sleep(0.3)

        assert_job_active(docker_redis_client, "prior-active-job-001", worker.hostname)
        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_PROCESSING)

    def test_completed_jobs_stay_completed_after_restart(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        job_id = "completed-after-restart-001"
        publish_job_request(docker_redis_client, job_id)
        time.sleep(0.3)
        worker.complete_job(job_id)
        time.sleep(0.3)
        assert_job_not_active(docker_redis_client, job_id)

        engine.stop()
        time.sleep(0.3)

        engine.start()
        time.sleep(0.3)

        assert_job_not_active(docker_redis_client, job_id)

    def test_recovery_dead_worker_with_jobs_requeues(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, hostname="dead-worker@test")
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        job_id = "dead-worker-job-001"
        publish_job_request(docker_redis_client, job_id)
        time.sleep(0.3)
        assert_job_active(docker_redis_client, job_id, worker.hostname)

        engine.stop()
        time.sleep(0.3)

        docker_redis_client.hset(worker.worker_key(), "status", WORKER_STATUS_OFFLINE)
        docker_redis_client.delete(worker.worker_key())

        engine.start()
        time.sleep(0.3)

        assert_job_not_active(docker_redis_client, job_id)
        queue = docker_redis_client.lrange(PENDING_QUEUE, 0, -1)
        assert job_id in queue, \
            f"Job {job_id} should be requeued after dead worker recovery"

    @pytest.mark.django_db(transaction=True)
    def test_startup_recovers_stuck_db_requests_and_jobs(self, engine, docker_redis_client):
        from apps.processing.models import BookCreationRequest, BookCreationRequestState, BookRecord
        from apps.ingestion.models import ProcessingJob, BookSubmission, SubmissionStatus, SubmissionInputType, ResolutionStatus
        
        # Stop engine to simulate it being down
        engine.stop()
        time.sleep(0.2)
        
        # Clear redis engine keys
        for key in docker_redis_client.scan_iter("engine:*"):
            docker_redis_client.delete(key)
            
        # Create a stuck BookCreationRequest in QUEUED state in DB
        record = BookRecord.objects.create(
            id="test-record-1",
            name="Test Record 1",
            url="https://example.com/books/test-1",
        )
        req = BookCreationRequest.objects.create(
            id="stuck-req-001",
            book_record=record,
            state=BookCreationRequestState.QUEUED,
        )
        
        # Create a stuck BookCreationRequest in PROCESSING state in DB
        record2 = BookRecord.objects.create(
            id="test-record-2",
            name="Test Record 2",
            url="https://example.com/books/test-2",
        )
        req2 = BookCreationRequest.objects.create(
            id="stuck-req-002",
            book_record=record2,
            state=BookCreationRequestState.PROCESSING,
        )
        
        # Create a stuck ProcessingJob in QUEUED state in DB
        submission = BookSubmission.objects.create(
            input_type=SubmissionInputType.URL,
            origin="user",
            original_input="https://example.com/books/test-job-1/",
            normalized_input="https://example.com/books/test-job-1/",
            resolved_url="https://example.com/books/test-job-1/",
            resolution_status=ResolutionStatus.RESOLVED,
            status=SubmissionStatus.QUEUED,
        )
        job = ProcessingJob.objects.create(
            id="00000000-0000-0000-0000-000000000001",
            submission=submission,
            job_type="reprocess",
            status="queued",
        )
        
        # Start the engine
        engine.start()
        time.sleep(0.3)
        
        # Verify the stuck database requests and jobs were queued in Redis
        queue = docker_redis_client.lrange(PENDING_QUEUE, 0, -1)
        assert "stuck-req-001" in queue
        assert "stuck-req-002" in queue
        assert "00000000-0000-0000-0000-000000000001" in queue
        
        # Verify the PROCESSING request was reverted to QUEUED in DB
        req2.refresh_from_db()
        assert req2.state == BookCreationRequestState.QUEUED
        
        # Verify handlers were set correctly in Redis
        assert docker_redis_client.hget("engine:job:handlers", "stuck-req-001") == "pipeline"
        assert docker_redis_client.hget("engine:job:handlers", "stuck-req-002") == "pipeline"
        assert docker_redis_client.hget("engine:job:handlers", "00000000-0000-0000-0000-000000000001") == "process_submission"
        
        # Cleanup
        req.delete()
        req2.delete()
        record.delete()
        record2.delete()
        job.delete()
        submission.delete()
