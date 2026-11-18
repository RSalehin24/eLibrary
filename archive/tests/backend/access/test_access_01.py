"""Compatibility facade for the named test_access_01 modules."""
from pathlib import Path as _Path

_MODULE_DIR = _Path(__file__).with_name("test_access_01_cases")
_MODULE_FILES = (
    "download_reader_and_kindle.py",
    "kindle_smtp_failures.py",
    "kindle_validation_and_html_downloads.py",

)

for _module_file in _MODULE_FILES:
    _module_path = _MODULE_DIR / _module_file
    exec(compile(_module_path.read_text(encoding="utf-8"), str(_module_path), "exec"), globals())

del _Path, _MODULE_DIR, _MODULE_FILES, _module_file, _module_path
