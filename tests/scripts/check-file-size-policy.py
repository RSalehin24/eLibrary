#!/usr/bin/env python3
"""Fail when first-party modules exceed the 300-line physical cap."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MAX_PHYSICAL_LINES = 300
POLICY_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".jsx",
    ".py",
    ".sh",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
EXCLUDED_DIR_PARTS = {
    ".git",
    "dist",
    "node_modules",
    "public",
    "storage",
    "vendor",
}
EXCLUDED_PREFIXES = (
    "docs/",
    "logs/",
)
EXCLUDED_FILENAMES = {
    "package-lock.json",
}


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


def load_policy_exemptions(root: Path) -> set[str]:
    exemptions = set()
    policy_dir = root / "tests" / "policy"
    if policy_dir.exists():
        for path in policy_dir.glob("*.txt"):
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    exemptions.add(line)
    return exemptions


def is_policy_target(path: str, exemptions: set[str]) -> bool:
    parts = set(Path(path).parts)
    if parts & EXCLUDED_DIR_PARTS:
        return False
    if path.startswith(EXCLUDED_PREFIXES):
        return False
    if Path(path).name in EXCLUDED_FILENAMES:
        return False
    if path in exemptions:
        return False
    return Path(path).suffix in POLICY_EXTENSIONS


def physical_line_count(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _line in handle)


def main() -> int:
    root = repo_root()
    exemptions = load_policy_exemptions(root)
    violations = []
    for rel_path in git_files(root):
        if not is_policy_target(rel_path, exemptions):
            continue
        absolute_path = root / rel_path
        if not absolute_path.is_file():
            continue
        line_count = physical_line_count(absolute_path)
        if line_count > MAX_PHYSICAL_LINES:
            violations.append((line_count, rel_path))

    if not violations:
        print(f"file-size policy passed: all target files <= {MAX_PHYSICAL_LINES} lines")
        return 0

    print(f"file-size policy failed: target files exceed {MAX_PHYSICAL_LINES} lines")
    for line_count, rel_path in sorted(violations, reverse=True):
        print(f"{line_count:4d} {rel_path}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
