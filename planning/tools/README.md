# Planning tools

Status: DRAFT

| Tool | Purpose |
|---|---|
| `check_plan.py` | Plan integrity: requirement ↔ invariant ↔ mechanism traceability, model coverage, link check, status rules, service templates, ADR sections, decision ids. Regenerates `02-requirements/traceability.generated.md`. |

Run from the repository root: `python3 planning/tools/check_plan.py` (standard library only; exit code 1 on error).
