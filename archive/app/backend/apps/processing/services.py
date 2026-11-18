"""Compatibility facade for the named services modules."""
from pathlib import Path as _Path

_MODULE_DIR = _Path(__file__).with_name("service_modules")
_MODULE_FILES = (
    "service_imports_and_constants.py",
    "catalog_phase_helpers.py",
    "catalog_phase_normalization.py",
    "catalog_progress_state.py",
    "checkpoint_and_runtime_adapters.py",
    "sync_status_messages.py",
    "state_serializers.py",
    "ui_projection_queries.py",
    "ui_domain_versions.py",
    "processing_state_queries.py",
    "catalog_record_sync.py",
    "incomplete_catalog_fetch.py",
    "sync_lifecycle_actions.py",
    "sync_completion.py",
    "automation_advancement.py",
    "incomplete_resolution.py",
    "sync_runner.py",
    "request_queue_runtime.py",
    "processing_table_queries.py",
    "processing_card_payloads.py",
    "automation_commands.py",
    "request_processing_persistence.py",
    "scrape_cache.py",
    "request_processing_pipeline.py",
    "maintenance_and_request_actions.py",
    "request_action_dispatch.py",

)

for _module_file in _MODULE_FILES:
    _module_path = _MODULE_DIR / _module_file
    exec(compile(_module_path.read_text(encoding="utf-8"), str(_module_path), "exec"), globals())

del _Path, _MODULE_DIR, _MODULE_FILES, _module_file, _module_path
