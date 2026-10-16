"""Deterministic local browser fixture command."""

from django.core.management.base import BaseCommand

from .seed_e2e_data_methods.catalog_processing_seed_records import (
    create_catalog_state,
    create_processing_state,
)
from .seed_e2e_data_methods.core_seed_records import (
    attach_asset,
    cleanup_existing_records,
    create_access_grants,
    create_access_user,
    create_books,
    create_processing_job_record,
    create_reader_state,
    create_submission_record,
    handle,
)
from .seed_e2e_data_methods.duplicate_review_seed_records import (
    create_automation_submissions,
    create_curation_submissions,
    create_duplicate_review,
)
from .seed_e2e_data_methods.submission_seed_records import create_submissions


class Command(BaseCommand):
    create_duplicate_review = create_duplicate_review
    create_automation_submissions = create_automation_submissions
    create_curation_submissions = create_curation_submissions
    help = "Reset and seed deterministic local E2E data for real browser tests."
    handle = handle
    cleanup_existing_records = cleanup_existing_records
    create_access_user = create_access_user
    create_books = create_books
    attach_asset = attach_asset
    create_access_grants = create_access_grants
    create_reader_state = create_reader_state
    create_submission_record = create_submission_record
    create_processing_job_record = create_processing_job_record
    create_submissions = create_submissions
    create_catalog_state = create_catalog_state
    create_processing_state = create_processing_state
