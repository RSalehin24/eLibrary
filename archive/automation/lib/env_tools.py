#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class EnvLine:
    raw: str
    key: str | None = None
    value: str | None = None


def parse_env_file(path: Path) -> list[EnvLine]:
    if not path.exists():
        return []

    lines: list[EnvLine] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.lstrip()
        if not raw_line or stripped.startswith("#") or "=" not in raw_line:
            lines.append(EnvLine(raw=raw_line))
            continue

        key, value = raw_line.split("=", 1)
        lines.append(EnvLine(raw=raw_line, key=key.strip(), value=value))
    return lines


def render_env_lines(lines: Iterable[EnvLine]) -> str:
    rendered_lines = (
        line.raw if line.key is None else f"{line.key}={line.value}"
        for line in lines
    )
    return "\n".join(rendered_lines) + "\n"


def scaffold_env(template_path: Path, target_path: Path) -> None:
    template_lines = parse_env_file(template_path)
    target_lines = parse_env_file(target_path)

    if not target_lines:
        target_path.write_text(render_env_lines(template_lines), encoding="utf-8")
        return

    existing_keys = {line.key for line in target_lines if line.key}
    missing_lines = [
        line for line in template_lines if line.key and line.key not in existing_keys
    ]
    if not missing_lines:
        return

    if target_lines and target_lines[-1].raw:
        target_lines.append(EnvLine(raw=""))
    target_lines.extend(missing_lines)
    target_path.write_text(render_env_lines(target_lines), encoding="utf-8")


def merge_env(base_path: Path, overrides_path: Path, output_path: Path, *, non_empty_only: bool) -> None:
    base_lines = parse_env_file(base_path)
    override_lines = parse_env_file(overrides_path)

    index_by_key = {
        line.key: index
        for index, line in enumerate(base_lines)
        if line.key is not None
    }

    for override_line in override_lines:
        if override_line.key is None:
            continue
        if non_empty_only and not (override_line.value or "").strip():
            continue

        if override_line.key in index_by_key:
            base_lines[index_by_key[override_line.key]] = EnvLine(
                raw="",
                key=override_line.key,
                value=override_line.value or "",
            )
            continue

        if base_lines and base_lines[-1].raw:
            base_lines.append(EnvLine(raw=""))
        base_lines.append(
            EnvLine(
                raw="",
                key=override_line.key,
                value=override_line.value or "",
            )
        )
        index_by_key[override_line.key] = len(base_lines) - 1

    output_path.write_text(render_env_lines(base_lines), encoding="utf-8")


def render_shell_exports(lines: Iterable[EnvLine]) -> str:
    rendered_lines = (
        f"export {line.key}={shlex.quote(line.value or '')}"
        for line in lines
        if line.key is not None
    )
    return "\n".join(rendered_lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Utilities for repo env files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = subparsers.add_parser(
        "scaffold",
        help="Create or extend an env file from a template.",
    )
    scaffold_parser.add_argument("template_file")
    scaffold_parser.add_argument("target_file")

    merge_parser = subparsers.add_parser(
        "merge",
        help="Merge one env file into another.",
    )
    merge_parser.add_argument("base_file")
    merge_parser.add_argument("override_file")
    merge_parser.add_argument("output_file")
    merge_parser.add_argument("--non-empty-only", action="store_true")

    shell_export_parser = subparsers.add_parser(
        "shell-export",
        help="Render shell export lines from an env file.",
    )
    shell_export_parser.add_argument("source_file")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scaffold":
        scaffold_env(Path(args.template_file), Path(args.target_file))
        return 0

    if args.command == "merge":
        merge_env(
            Path(args.base_file),
            Path(args.override_file),
            Path(args.output_file),
            non_empty_only=args.non_empty_only,
        )
        return 0

    if args.command == "shell-export":
        print(render_shell_exports(parse_env_file(Path(args.source_file))))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
