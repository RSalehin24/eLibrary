# Machine handover — 28 October 2026

This is the current handover for continuing the application → reader → engine
implementation on another machine. It supersedes runtime, implementation-status
and verification claims in [the historical handoff](../../implementation-handoff.md).
Historical evidence remains useful, but is not acceptance of the current changes.

**The project is not complete.** Website implementation is in progress at M1/W08.
Independent reader and engine implementation have not started. No milestone has
user visual/UX acceptance. The latest complete Chromium run has unresolved failures.

## Read in this order

1. [Transfer the working tree and private data](transfer.md).
2. [Implementation state and changed modules](implementation-state.md).
3. [Prepare and start the new machine](machine-setup.md).
4. [Verification results, failures and next steps](verification-and-next-steps.md).
5. The original [requirements](../../application-reader-engine-plan.md), reviewed
   [module plans](../../application-reader-engine-implementation/README.md) and
   [task order](../../application-reader-engine-implementation/shared/baseline-and-sequence.md).

## Important transfer facts

| Item | Checkpoint |
| --- | --- |
| Source machine directory | `/Users/rsalehin24/Documents/elibrary` |
| Branch | `reyan-new-version` |
| Git HEAD | `4f4db6c5dd4e2609d4a2df2c172d7924a2e44445` |
| Implementation changes | Uncommitted; many required files are untracked |
| Snapshot before this handover | 352 tracked files changed; 423 Git status entries including untracked files |
| Current browser inventory | 60 specifications; latest full run selected the preceding 59 |
| Source Markdown SHA-256 | `46fd596d22b5f730f3b06fa8c2458c594d2f4a4cfb3efefa765cb2674ea78c96` |
| Source PDF SHA-256 | `f7546a970d9e7cb899232e76481b9d329daa237c7ad388e91138eb2aad1ee3a8` |

Counts are a checkpoint, not a frozen transfer manifest; this documentation adds
files. A clone or HEAD checkout alone will lose the implementation, original
untracked specification/PDF, reviewed plans, new migrations and regressions.
Transfer the whole working tree, including deletions and `.git`, or use an
equivalent verified transfer that preserves all three kinds of changes.

## Current runtime observation

On 28 October, no task API, Next.js, Playwright or isolated-runner process was
found. Docker could not connect to the old Colima socket. No services were started,
database contents inspected, migrations applied or live jobs resumed for this
handover. Old process/session IDs must not be reused.

The preceding implementation used reference API **8002**, website **3001**,
PostgreSQL **55432**, and a dedicated test Redis **56380**. These are reproduction
settings, not promises that anything is currently running.

## Rules for the receiving developer/agent

- Read the transferred root `AGENTS.md`; it is ignored by Git and must be copied
  explicitly. Follow nearer instructions if present. No subagents were authorized.
- Continue the existing changes. Do not reset, clean, regenerate all plans, replace
  the working tree with HEAD, or discard files because they are untracked.
- Do not add dependencies, commit, push, deploy or send external mail/Kindle content
  without the authorization required by the project/user instructions.
- Keep `bangla_library_preview` separate. It has not received these migrations or
  synthetic fixtures. Never point the fixture seeder at it.
- Keep delivery, processing and scheduler workers off during reference verification.
  Do not purge unrelated queues, clear host Redis or start the legacy whole stack.
- Preserve generated contracts and new migrations; generate changes with repository
  tools. Do not hand-edit historical migrations, generated schema/types or lockfiles.
- Keep original failed evidence and fix causes. Do not lower assertions, disable
  throttles, suppress types/lint, or count interrupted/stale runs as passes.

## Continuation prompt

Copy this into the new coding session after transferring the repository:

> Continue the application-reader-engine implementation from
> `docs/application-reader-engine-progress/handover/README.md`. Read all linked
> handover files and AGENTS.md first. Preserve the entire uncommitted working tree.
> Recreate the isolated reference environment, rebuild the latest source, investigate
> and fix the recorded browser failures, and finish current website verification.
> Do not seed or migrate the separate user preview, send external mail, start
> background delivery, commit, push or deploy. W08 requires recorded user visual/UX
> acceptance before reader extraction; R05 precedes engine implementation. Report
> actual verification and remaining gaps without claiming a zero-defect guarantee.

The handover documents describe how to resume; **no archive, database dump, remote
copy or new-machine setup has been performed** as part of preparing them.
