#!/usr/bin/env python3
"""Fail when first-party modules violate the refactor architecture guardrails."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


SOURCE_EXTENSIONS = {".js", ".jsx", ".py", ".sh", ".ts", ".tsx"}
EXCLUDED_DIR_PARTS = {
    ".git",
    "dist",
    "node_modules",
    "public",
    "storage",
    "vendor",
}
NUMBERED_SPLIT_MODULE_PATTERN = re.compile(r"(^|/)(part[-_]\d+)(\.|/|$)")
GENERATED_SPLIT_LOADER_PATTERNS = (
    "Generated loader preserving the public module path",
    'glob("part_*.py")',
    "glob('part_*.py')",
    '"/part_*.sh"',
    "'/part_*.sh'",
)
FRONTEND_API_CLIENT_RE = re.compile(
    r"^app/frontend/src/(api/|features/[^/]+/api\.(?:js|jsx|ts|tsx)$)"
)
TRANSPORT_IO_IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+(redis|requests|kombu|bs4|boto3|celery|config\.celery)\b",
    re.MULTILINE,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def git_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def is_first_party_source(path: str) -> bool:
    parts = set(Path(path).parts)
    if parts & EXCLUDED_DIR_PARTS:
        return False
    return Path(path).suffix in SOURCE_EXTENSIONS


def is_transport_module(path: str) -> bool:
    if not path.startswith("app/backend/apps/") or not path.endswith(".py"):
        return False
    return "/views/" in path or path.endswith("/views.py") or "/serializers/" in path


def main() -> int:
    root = repo_root()
    violations: list[str] = []

    for rel_path in git_files(root):
        if not is_first_party_source(rel_path):
            continue

        path = root / rel_path
        if not path.is_file():
            continue

        if NUMBERED_SPLIT_MODULE_PATTERN.search(rel_path) or "_parts/" in rel_path:
            violations.append(f"{rel_path}: numbered split module paths are not allowed")

        content = path.read_text(encoding="utf-8", errors="ignore")

        if rel_path != "tests/scripts/check-architecture-policy.py" and any(
            pattern in content for pattern in GENERATED_SPLIT_LOADER_PATTERNS
        ):
            violations.append(f"{rel_path}: generated part-module loader is not allowed")

        if (
            rel_path.startswith("app/frontend/src/")
            and Path(rel_path).suffix in {".js", ".jsx", ".ts", ".tsx"}
            and "apiFetch" in content
            and not FRONTEND_API_CLIENT_RE.match(rel_path)
        ):
            violations.append(f"{rel_path}: import API calls through an API-client module")

        if is_transport_module(rel_path) and TRANSPORT_IO_IMPORT_RE.search(content):
            violations.append(f"{rel_path}: transport modules must not import external I/O clients")

    if not violations:
        print("architecture policy passed")
        return 0

    print("architecture policy failed")
    for violation in violations:
        print(violation)
    return 1


if __name__ == "__main__":
    sys.exit(main())
