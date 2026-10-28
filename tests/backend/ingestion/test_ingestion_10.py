"""Compatibility facade for the named test_ingestion_10 modules."""

from importlib import import_module as _import_module

_MODULE_FILES = (
    "scraper_crawl_and_cover.py",
    "queue_fallback_and_retries.py",
    "queue_fallback_and_retries_additional.py",
    "stale_task_dispatch_guards.py",
    "stale_task_dispatch_guards_additional.py",
    "stale_processing_recovery.py",
)

for _module_file in _MODULE_FILES:
    _module = _import_module(
        f"tests.backend.ingestion.test_ingestion_10_cases.{_module_file[:-3]}"
    )
    globals().update(
        {
            name: value
            for name, value in vars(_module).items()
            if not name.startswith("_")
        }
    )

del _import_module, _MODULE_FILES, _module_file, _module
