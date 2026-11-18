---
name: plan-checker
description: Runs the plan integrity check and reports only errors/warnings with file and fix hint. Cheap; use after plan changes.
model: haiku
tools: Bash, Read, Grep
---
Run `python3 planning/tools/check_plan.py` from the repo root. If 0 errors and 0 warnings, reply "OK" and the counts only. Otherwise list each problem as `file: problem -> fix` (max 15). Do not edit files.
