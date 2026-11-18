---
name: fanout
description: Split a task into independent pieces and run them in parallel with minimal context. Use for multi-doc/multi-service work.
disable-model-invocation: true
---
1. List the pieces; each must touch a disjoint set of files and need no other piece's output. Anything shared (STATUS, DECISIONS, traceability, index READMEs) stays with you, done last.
2. Launch all pieces in ONE message: `plan-writer` for edits, `plan-reviewer` for read-only review, `Explore` for searches. Give each: exact files, the goal, the output limit (<=8 lines). Use `isolation: worktree` only for code that may conflict.
3. Do not re-read what agents already summarised. Merge their open questions into one AskUserQuestion call (max 4 questions).
4. Finish with `plan-checker`, then update STATUS.md.
