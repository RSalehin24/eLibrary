"""Compatibility facade for the named views modules."""
from pathlib import Path as _Path

_MODULE_DIR = _Path(__file__).with_name("view_modules")
_MODULE_FILES = (
    "auth_and_password_views.py",
    "totp_profile_managed_user_views.py",

)

for _module_file in _MODULE_FILES:
    _module_path = _MODULE_DIR / _module_file
    exec(compile(_module_path.read_text(encoding="utf-8"), str(_module_path), "exec"), globals())

del _Path, _MODULE_DIR, _MODULE_FILES, _module_file, _module_path
