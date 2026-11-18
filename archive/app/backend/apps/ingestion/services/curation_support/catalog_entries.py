"""Compatibility facade for the named catalog_entries modules."""
from pathlib import Path as _Path

_MODULE_DIR = _Path(__file__).with_name("catalog_entry_modules")
_MODULE_FILES = (
    "entry_inspection_queries.py",
    "snapshot_summaries.py",

)

for _module_file in _MODULE_FILES:
    _module_path = _MODULE_DIR / _module_file
    exec(compile(_module_path.read_text(encoding="utf-8"), str(_module_path), "exec"), globals())

del _Path, _MODULE_DIR, _MODULE_FILES, _module_file, _module_path
