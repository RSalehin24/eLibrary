#!/bin/sh
# After an edit under planning/, run the plan check; silent on success (no tokens spent).
f=$(jq -r '.tool_input.file_path // empty')
case "$f" in
  */planning/*.md|*/planning/tools/*) ;;
  *) exit 0 ;;
esac
cd "$(dirname "$0")/../.." || exit 0
out=$(python3 planning/tools/check_plan.py 2>&1) && exit 0
printf '%s\n' "$out" | grep -iE 'error|fail' | head -15 >&2
exit 2
