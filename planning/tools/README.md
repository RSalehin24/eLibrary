# Planning tools

Status: DRAFT

| Tool | Purpose |
|---|---|
| `check_plan.py` | Plan integrity: requirement ↔ invariant ↔ mechanism traceability, model coverage, link check, status rules, service templates, ADR sections, decision ids. Regenerates `02-requirements/traceability.generated.md`. |

| `model_mirror.py` | Python mirrors of the TLA+/Alloy models (interim evidence while Java/TLC is unavailable). Bounds via `MIRROR_JOBS`, `MIRROR_ATTEMPTS`, `MIRROR_STATE_LIMIT`. Run under a memory cap, e.g. `(ulimit -v 20000000; timeout 900 python3 -I -u planning/tools/model_mirror.py all)`. |

Run `check_plan.py` from the repository root: `python3 planning/tools/check_plan.py` (standard library only; exit code 1 on error).
