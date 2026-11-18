"""Compatibility facade for the named submissions modules."""
from pathlib import Path as _Path

_MODULE_DIR = _Path(__file__).with_name("submission_modules")
_MODULE_FILES = (
    "job_lifecycle.py",
    "retry_and_deduplication.py",
    "resolution_and_queueing.py",
    "book_persistence.py",
    "processing_job_runner.py",

)

for _module_file in _MODULE_FILES:
    _module_path = _MODULE_DIR / _module_file
    exec(compile(_module_path.read_text(encoding="utf-8"), str(_module_path), "exec"), globals())

del _Path, _MODULE_DIR, _MODULE_FILES, _module_file, _module_path
