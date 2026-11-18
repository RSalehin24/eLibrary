"""Compatibility facade for the named normalization modules."""
from pathlib import Path as _Path

_MODULE_DIR = _Path(__file__).with_name("normalization_modules")
_MODULE_FILES = (
    "front_matter_text_rules.py",
    "front_matter_detection.py",
    "content_segment_extraction.py",
    "scraped_book_normalization.py",

)

for _module_file in _MODULE_FILES:
    _module_path = _MODULE_DIR / _module_file
    exec(compile(_module_path.read_text(encoding="utf-8"), str(_module_path), "exec"), globals())

del _Path, _MODULE_DIR, _MODULE_FILES, _module_file, _module_path
