"""Compatibility facade for the named test_processing_api modules."""

from importlib import import_module as _import_module

_MODULE_FILES = (
    "helpers.py",
    "catalog_matrix_helpers.py",
    "catalog_manual_matrix_cases.py",
    "catalog_automation_matrix_cases.py",
    "incomplete_catalog_and_domain_versions.py",
    "catalog_sync_persistence.py",
    "runtime_tick_and_projection_reads.py",
    "read_endpoint_purity.py",
    "ui_version_publication.py",
    "state_payload_and_tables.py",
    "automation_ownership_flows.py",
    "catalog_phase_resume_flows.py",
    "catalog_phase_resume_flows_additional.py",
    "catalog_phase_matrix_tests.py",
    "catalog_phase_serialization.py",
    "catalog_sync_parallel.py",
    "catalog_phase_pause_behaviour.py",
    "incomplete_automation_flows.py",
    "processing_pipeline_dispatch.py",
    "checkpoint_and_dispatch_recovery.py",
    "stale_recovery.py",
    "queue_fallback_and_reset.py",
    "maintenance_and_actions.py",
    "duplicate_resolution_actions.py",
    "duplicate_resolution_actions_additional.py",
    "automation_persistence.py",
)

for _module_file in _MODULE_FILES:
    _module = _import_module(
        f"tests.backend.processing.test_processing_api_cases.{_module_file[:-3]}"
    )
    globals().update(
        {
            name: value
            for name, value in vars(_module).items()
            if not name.startswith("_")
        }
    )

del _import_module, _MODULE_FILES, _module_file, _module
