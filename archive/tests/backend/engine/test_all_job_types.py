"""Tests for Central Job Engine: All Job Types.

Verifies that the Engine correctly handles all job types including
reprocessing, ingestion, curation, automation, and catalog sync.
"""

import json
import time

import pytest

from .constants import *
from .helpers import *


class TestReprocessJobs:
    """Reprocess job type handling."""

    def test_reprocess_job_dispatched(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, capabilities=["process_submission"])
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "reprocess-job-001"
        publish_job_request(docker_redis_client, job_id, job_type="reprocess", handler="process_submission")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )

    def test_reprocess_job_completion(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, capabilities=["process_submission"])
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "reprocess-complete-001"
        publish_job_request(docker_redis_client, job_id, job_type="reprocess", handler="process_submission")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )

        worker.complete_job(job_id)
        assert wait_for_condition(
            lambda: docker_redis_client.hget(ACTIVE_JOBS, job_id) is None,
            timeout=3.0,
        )


class TestIngestionJobs:
    """Ingestion (catalog) job type handling."""

    def test_ingestion_job_dispatched(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, capabilities=["catalog_sync"])
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "ingestion-job-001"
        publish_job_request(docker_redis_client, job_id, job_type="ingestion", handler="catalog_sync")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )

    def test_ingestion_job_requires_catalog_worker(self, engine, docker_redis_client):
        process_worker = FakeWorker(docker_redis_client, capabilities=["process_submission"], hostname="proc-worker@test")
        catalog_worker = FakeWorker(docker_redis_client, capabilities=["catalog_sync"], hostname="cat-worker@test")
        process_worker.register()
        catalog_worker.register()

        job_id = "ingestion-no-proc-001"
        publish_job_request(docker_redis_client, job_id, job_type="ingestion", handler="catalog_sync")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, catalog_worker.hostname, timeout=3.0,
        )


class TestCurationJobs:
    """Curation job type handling."""

    def test_curation_job_dispatched(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, capabilities=["curation"])
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "curation-job-001"
        publish_job_request(docker_redis_client, job_id, job_type="curation", handler="curation")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )

    def test_curation_job_routed_to_curation_worker(self, engine, docker_redis_client):
        process_worker = FakeWorker(docker_redis_client, capabilities=["process_submission"], hostname="proc-worker@test")
        curation_worker = FakeWorker(docker_redis_client, capabilities=["curation"], hostname="cur-worker@test")
        process_worker.register()
        curation_worker.register()

        job_id = "curation-routing-001"
        publish_job_request(docker_redis_client, job_id, job_type="curation", handler="curation")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, curation_worker.hostname, timeout=3.0,
        )


class TestAutomationJobs:
    """Automation job type handling."""

    def test_automation_job_dispatched(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, capabilities=["automation"])
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "automation-job-001"
        publish_job_request(docker_redis_client, job_id, job_type="automation", handler="automation")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )


class TestCatalogSyncJobs:
    """Catalog sync job type handling."""

    def test_catalog_sync_job_dispatched(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, capabilities=["catalog_sync"])
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "catalogsync-job-001"
        publish_job_request(docker_redis_client, job_id, job_type="catalog_sync", handler="catalog_sync")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )


class TestMixedJobTypes:
    """Multiple job types handled concurrently by the same Engine."""

    def test_mixed_job_types_routed_correctly(self, engine, docker_redis_client):
        process_worker = FakeWorker(docker_redis_client, capabilities=["process_submission"], hostname="proc-worker@test")
        catalog_worker = FakeWorker(docker_redis_client, capabilities=["catalog_sync"], hostname="cat-worker@test")
        process_worker.register()
        catalog_worker.register()

        reprocess_job = "mixed-reprocess-001"
        catalog_job = "mixed-catalog-001"

        publish_job_request(docker_redis_client, reprocess_job, job_type="reprocess", handler="process_submission")
        publish_job_request(docker_redis_client, catalog_job, job_type="ingestion", handler="catalog_sync")

        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, reprocess_job, process_worker.hostname, timeout=3.0,
        )
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, catalog_job, catalog_worker.hostname, timeout=3.0,
        )

    def test_unknown_job_type_queued_no_matching_worker(self, engine, docker_redis_client):
        """Unknown job types with no matching worker capability are queued."""
        worker = FakeWorker(docker_redis_client, capabilities=["process_submission"])
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "unknown-type-001"
        publish_job_request(docker_redis_client, job_id, job_type="unknown", handler="unknown_handler")
        assert wait_for_queue_length(docker_redis_client, 1, timeout=3.0), \
            "Unknown job types should be queued if no worker has matching capability"
        assert_job_not_active(docker_redis_client, job_id)
