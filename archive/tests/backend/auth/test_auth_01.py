"""Compatibility facade for the named test_auth_01 modules."""
from pathlib import Path as _Path

_MODULE_DIR = _Path(__file__).with_name("test_auth_01_cases")
_MODULE_FILES = (
    "totp_and_managed_user_invites.py",
    "password_reset_flow.py",
    "managed_user_admin_flow.py",
    "password_setup_and_totp_invites.py",

)

for _module_file in _MODULE_FILES:
    _module_path = _MODULE_DIR / _module_file
    exec(compile(_module_path.read_text(encoding="utf-8"), str(_module_path), "exec"), globals())

del _Path, _MODULE_DIR, _MODULE_FILES, _module_file, _module_path
