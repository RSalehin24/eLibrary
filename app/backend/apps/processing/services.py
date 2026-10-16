"""Retained processing API; implementation modules use regular imports.

The legacy module exposes hundreds of historical names. Keep compatibility
without executing source files or merging implementation namespaces.
"""

from .service_modules import (
    automation_advancement,
    automation_commands,
    automation_schedule,
    catalog_phase_helpers,
    catalog_phase_normalization,
    catalog_progress_state,
    catalog_record_sync,
    catalog_refresh,
    checkpoint_and_runtime_adapters,
    incomplete_catalog_fetch,
    incomplete_catalog_queries,
    incomplete_resolution,
    maintenance_and_request_actions,
    processing_card_payloads,
    processing_state_queries,
    processing_table_queries,
    remote_record_queries,
    request_action_dispatch,
    request_pipeline_tick,
    request_processing_persistence,
    request_processing_pipeline,
    request_queue_runtime,
    runtime_dependencies,
    scrape_cache,
    service_imports_and_constants,
    state_serializers,
    sync_completion,
    sync_lifecycle_actions,
    sync_runner,
    sync_status_messages,
    ui_domain_versions,
    ui_projection_queries,
)

_EXPORT_MODULES = (
    catalog_refresh,
    automation_schedule,
    incomplete_catalog_queries,
    request_pipeline_tick,
    remote_record_queries,
    runtime_dependencies,
    request_action_dispatch,
    maintenance_and_request_actions,
    request_processing_pipeline,
    scrape_cache,
    request_processing_persistence,
    automation_commands,
    processing_card_payloads,
    processing_table_queries,
    request_queue_runtime,
    sync_runner,
    incomplete_resolution,
    automation_advancement,
    sync_completion,
    sync_lifecycle_actions,
    incomplete_catalog_fetch,
    catalog_record_sync,
    processing_state_queries,
    ui_domain_versions,
    ui_projection_queries,
    state_serializers,
    sync_status_messages,
    checkpoint_and_runtime_adapters,
    catalog_progress_state,
    catalog_phase_normalization,
    catalog_phase_helpers,
    service_imports_and_constants,
)
__all__ = [
    name
    for name in sorted(
        {
            name
            for module in _EXPORT_MODULES
            for name in vars(module)
            if not name.startswith("_")
        }
    )
]


def __getattr__(name):
    for module in _EXPORT_MODULES:
        if name in vars(module) and not name.startswith("__"):
            return getattr(module, name)
    raise AttributeError(f"{__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
