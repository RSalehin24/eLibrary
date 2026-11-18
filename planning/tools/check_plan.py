#!/usr/bin/env python3
"""Plan integrity checker.

Enforces the planning rules so the plan cannot silently drift:

1. Every REQ is defined once and names >= 1 invariant and >= 1 verification method.
2. Every invariant referenced by a REQ is defined in the invariants register.
3. Every invariant is referenced by at least one REQ, and names a known mechanism.
4. Invariants whose mechanism is `model` have a matching model reference in
   03-correctness/formal-models/coverage.md.
5. Every relative Markdown link resolves.
6. Every document has a `Status:` line; ACCEPTED docs contain no TBD/TODO/???.
7. Every service folder has the required template files.
8. Every ADR has Status and Decision sections; open decisions are listed once.
9. Working-agreement files exist (STATUS, DECISIONS, INCONSISTENCIES, philosophy,
   coding standards, dependency policy) and no decision id is both answered and open.

Writes 02-requirements/traceability.generated.md. Exit code 1 on any error.
Usage: python3 planning/tools/check_plan.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQ_RE = re.compile(r"^- \*\*(REQ-[A-Z]{3}-\d{3})\*\*\s*·\s*(MUST|SHOULD|COULD)\s*·\s*inv:\s*([^·]+?)\s*·\s*verify:\s*([^·]+?)\s*·\s*(.+)$")
INV_RE = re.compile(r"^- \*\*(INV-[A-Z]{3}-\d{3})\*\*\s*·\s*([a-z ,]+?)\s*·\s*by:\s*([^·]+?)\s*·\s*(.+)$")
LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")
VERIFY = {"type", "db", "model", "prop", "unit", "e2e", "gold", "fuzz", "review", "drill"}
SERVICE_FILES = ["README.md", "domain-model.md", "api-contract.md", "state-machines.md", "test-plan.md"]
SERVICES = ["identity", "catalog", "reader", "ingestion", "notify"]
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|FIXME)\b|\?\?\?")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def md_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if "tools" not in p.relative_to(ROOT).parts or p.name == "README.md")


def parse_requirements():
    reqs = {}
    for path in sorted((ROOT / "02-requirements").glob("*.md")):
        if path.name.startswith("traceability"):
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("- **REQ-"):
                m = REQ_RE.match(line)
                if not m:
                    err(f"{path.relative_to(ROOT)}:{n}: malformed requirement line")
                    continue
                rid, prio, invs, verify, text = m.groups()
                inv_list = [i.strip() for i in invs.split(",") if i.strip()]
                ver_list = [v.strip() for v in verify.split(",") if v.strip()]
                if rid in reqs:
                    err(f"{rid}: defined twice")
                bad = [v for v in ver_list if v not in VERIFY]
                if bad:
                    err(f"{rid}: unknown verify method(s) {bad}")
                if not inv_list or not ver_list:
                    err(f"{rid}: needs invariant and verification method")
                reqs[rid] = dict(prio=prio, invs=inv_list, verify=ver_list, text=text, file=path.name)
    return reqs


def parse_invariants():
    invs = {}
    path = ROOT / "03-correctness" / "invariants-register.md"
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("- **INV-"):
            m = INV_RE.match(line)
            if not m:
                err(f"{path.relative_to(ROOT)}:{n}: malformed invariant line")
                continue
            iid, owner, by, text = m.groups()
            by_list = [b.strip() for b in by.split(",") if b.strip()]
            bad = [b for b in by_list if b not in VERIFY]
            if bad:
                err(f"{iid}: unknown mechanism(s) {bad}")
            if iid in invs:
                err(f"{iid}: defined twice")
            invs[iid] = dict(owner=owner.strip(), by=by_list, text=text)
    return invs


def check_trace(reqs, invs):
    used = set()
    for rid, r in reqs.items():
        for i in r["invs"]:
            used.add(i)
            if i not in invs:
                err(f"{rid}: references undefined invariant {i}")
    for iid in invs:
        if iid not in used:
            err(f"{iid}: not referenced by any requirement")
    # model coverage
    cov = (ROOT / "03-correctness" / "formal-models" / "coverage.md")
    cov_text = cov.read_text(encoding="utf-8") if cov.exists() else ""
    for iid, i in invs.items():
        if "model" in i["by"] and iid not in cov_text:
            err(f"{iid}: mechanism 'model' but not listed in formal-models/coverage.md")
    return used


def check_links():
    for path in md_files():
        text = path.read_text(encoding="utf-8")
        in_code = False
        for n, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            for target in LINK_RE.findall(line):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                t = target.split("#")[0]
                if not t:
                    continue
                dest = (path.parent / t).resolve()
                if not dest.exists():
                    err(f"{path.relative_to(ROOT)}:{n}: broken link -> {target}")


def check_status():
    for path in md_files():
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^Status:\s*(\w+)", text, re.M)
        if not m:
            err(f"{path.relative_to(ROOT)}: missing 'Status:' line")
            continue
        if m.group(1) == "ACCEPTED" and PLACEHOLDER_RE.search(text):
            err(f"{path.relative_to(ROOT)}: ACCEPTED doc contains placeholder text")


def check_services():
    for s in SERVICES:
        d = ROOT / "05-services" / s
        for f in SERVICE_FILES:
            if not (d / f).exists():
                err(f"05-services/{s}: missing {f}")
    for s in ("web",):
        if not (ROOT / "05-services" / s / "README.md").exists():
            err(f"05-services/{s}: missing README.md")


def check_adrs():
    adr_dir = ROOT / "04-architecture" / "adr"
    for p in sorted(adr_dir.glob("[0-9]*.md")):
        t = p.read_text(encoding="utf-8")
        for sec in ("## Context", "## Decision", "## Consequences"):
            if sec not in t:
                err(f"{p.relative_to(ROOT)}: missing section {sec}")
    od = ROOT / "04-architecture" / "open-decisions.md"
    ids = re.findall(r"^\| (D-\d\d) \|", od.read_text(encoding="utf-8"), re.M)
    if len(ids) != len(set(ids)):
        err("open-decisions.md: duplicate decision ids")


REQUIRED_ROOT = ["STATUS.md", "DECISIONS.md", "INCONSISTENCIES.md",
                 "00-charter/engineering-philosophy.md", "00-charter/working-agreement.md",
                 "03-correctness/coding-standards.md", "04-architecture/dependency-policy.md"]


def check_working_agreement():
    for rel in REQUIRED_ROOT:
        if not (ROOT / rel).exists():
            err(f"{rel}: required file missing")
    decisions = (ROOT / "DECISIONS.md")
    opened = (ROOT / "04-architecture" / "open-decisions.md")
    if decisions.exists() and opened.exists():
        answered = set(re.findall(r"^\| (D-\d\d) \|", decisions.read_text(encoding="utf-8"), re.M))
        still_open = set(re.findall(r"^\| (D-\d\d) \|", opened.read_text(encoding="utf-8"), re.M))
        for both in sorted(answered & still_open):
            err(f"{both}: listed as answered in DECISIONS.md and open in open-decisions.md")


def check_decision_format():
    """Every open decision must list >= 2 options and a recommendation (owner rule)."""
    path = ROOT / "04-architecture" / "open-decisions.md"
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not re.match(r"^\| D-\d\d \|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            err(f"open-decisions.md:{n}: needs ID | Decision | Options | Recommendation | Blocks")
            continue
        if len([o for o in cells[2].split("·") if o.strip()]) < 2:
            err(f"open-decisions.md:{n}: {cells[0]} needs at least two options separated by ' · '")
        if not cells[3]:
            err(f"open-decisions.md:{n}: {cells[0]} needs a recommendation")
    claude = ROOT.parent / "CLAUDE.md"
    if claude.exists() and "AskUserQuestion" not in claude.read_text(encoding="utf-8"):
        err("CLAUDE.md: decision-request rule (AskUserQuestion) missing")
    if not claude.exists():
        err("CLAUDE.md: repository root file missing")


def write_matrix(reqs, invs):
    out = ["# Traceability matrix (generated)", "", "Status: DRAFT", "",
           "Generated by `tools/check_plan.py`. Do not edit.", "",
           f"{len(reqs)} requirements · {len(invs)} invariants", "",
           "| Requirement | Priority | Invariants | Mechanisms (invariant) | Verification (requirement) |",
           "|---|---|---|---|---|"]
    for rid in sorted(reqs):
        r = reqs[rid]
        mech = sorted({m for i in r["invs"] if i in invs for m in invs[i]["by"]})
        out.append(f"| {rid} | {r['prio']} | {', '.join(r['invs'])} | {', '.join(mech)} | {', '.join(r['verify'])} |")
    out += ["", "## Mechanism usage", "", "| Mechanism | Invariants |", "|---|---|"]
    count = {}
    for i in invs.values():
        for m in i["by"]:
            count[m] = count.get(m, 0) + 1
    for m in sorted(count):
        out.append(f"| {m} | {count[m]} |")
    (ROOT / "02-requirements" / "traceability.generated.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    reqs = parse_requirements()
    invs = parse_invariants()
    check_trace(reqs, invs)
    check_links()
    check_status()
    check_services()
    check_adrs()
    check_working_agreement()
    check_decision_format()
    write_matrix(reqs, invs)
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n{len(reqs)} requirements, {len(invs)} invariants, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
