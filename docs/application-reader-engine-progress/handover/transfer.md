# Transfer and preservation

This is a transfer checklist, not a record that a transfer or backup has occurred.
The source tree is uncommitted. Do not use a clean clone as the complete project.

## Required source material

Transfer the project directory to the trusted new machine using an encrypted
channel or encrypted storage. Preserve hidden files and Git metadata. Required:

- `.git/`, tracked modifications, intentionally deleted tracked paths, and every
  non-ignored untracked implementation/test/documentation file.
- Root `AGENTS.md`, which is Git-ignored. Its absence would lose mandatory project
  rules. Also preserve any nearer instruction files discovered at transfer time.
- `docs/application-reader-engine-plan.md` and `.pdf`, both currently untracked.
- Entire `docs/application-reader-engine-implementation/` planning package,
  including requirements mappings, validator, validator tests and fingerprint file.
- Entire progress directory, including this handover and baseline CSVs.
- All new generated migrations, source modules and regressions; see Git status.
- Both package lockfiles, Python requirements/constraints, Compose/deployment and
  test tooling. Do not substitute new dependency versions during relocation.

Prefer a full directory copy to a new destination. It naturally preserves absent
tracked paths. If overlaying onto a clone, separately reconcile deletions; merely
copying changed/new files can resurrect removed APIs, pages and review modules.
Do not run `git clean`, `reset --hard`, force checkout or destructive synchronization
to make the destination resemble a clean repository.

Before copying, stop any task writers only after identifying their ownership.
On the 28 October inspection none of the task serving/test processes was running;
Docker was unavailable. Recheck if work resumes before transfer.

## Capture transfer evidence

From the repository root, save these outputs in a private transfer directory
outside the repository. They contain filenames/status, not environment contents:

```sh
git rev-parse HEAD > "$TRANSFER_DIR/git-head.txt"
git branch --show-current > "$TRANSFER_DIR/git-branch.txt"
git status --porcelain=v1 --untracked-files=all > "$TRANSFER_DIR/git-status.txt"
git diff --binary HEAD > "$TRANSFER_DIR/tracked-changes.patch"
git ls-files --others --exclude-standard > "$TRANSFER_DIR/untracked-files.txt"
```

Set `TRANSFER_DIR` to a private existing directory first. The patch is supplemental:
it excludes untracked files and ignored `AGENTS.md`, so **it is not a full backup**.
Private diffs can contain application data; keep these records private too.

After copying, compare HEAD/branch, Git status and source hashes on both machines.
Check content for untracked files, not just their presence. Preserve filesystem
permissions for private fixtures. The new path can differ; replace old absolute
paths in environment settings, not in historical raw evidence.

## Rebuild rather than depend on copied runtime products

The following are machine-specific and can be recreated: `.venv`, `node_modules`,
`.next`, generated runtime caches, Python bytecode, Playwright browser bundles,
temporary proxy/server files and process IDs. A full copy may include them, but
do not use the copied virtual environment or build as new-machine verification.
Keep old artifacts until the transfer is validated; no deletion is necessary.

Install from existing requirements/constraints and npm lockfiles. Build `app/web`
on the new machine. CPU architecture/OS changes particularly require fresh native
dependencies and browser bundles.

## Private evidence, corpus and data

`test-artifacts/`, backend storage, `.env` files, database volumes and many credentials
are ignored by Git. Decide explicitly which private material must accompany source:

| Material | Treatment |
| --- | --- |
| `test-artifacts/foundation/implementation-*` | Transfer current logs, layout JSON/screenshots and failed-run evidence for audit continuity |
| Private fixture JSON, traces, auth screenshots | Credentials/session/link tokens may be present; encrypted/private transfer only, never print or commit |
| `implementation-reference-media/` | Disposable synthetic reference assets; may instead regenerate with fresh fixtures |
| `bangla_library` | Disposable browser reference; clean initialization is supported |
| `test_bangla_library` | Disposable pytest DB; recreate rather than transport |
| `bangla_library_preview` plus its media | Separate user preview; preserve privately if needed, never seed synthetic data or automatically migrate it |
| Source corpus/cache, EPUB/HTML, provenance, annotations | Preserve required real inputs with matching DB/media/runtime records for later corpus work; inventory exact locations before copying |
| Broker/Redis state | Not required for clean website reference tests; never restore and automatically consume old delivery/processing queues |
| `.env`, source authentication, SMTP/TLS/host credentials | Recreate or transfer separately through a secure channel; no values belong in this handover |

No database dump has been taken for this task. If preserving an existing user
database, take a PostgreSQL logical backup and matching media/runtime snapshot
with its writers stopped. Verify checksums and restore into a **separate** target
before using it. Do not cold-copy live database files between OS/architectures.
The existing [restore/deployment procedures](../../operations/platform-deployment.md)
are historical tooling references; review their scope before running them.

Do not rename a preview dump to `bangla_library` and then run the synthetic seeder.
Keep real user data and synthetic verification environments separately identified.
Preserve the original preview and backups even though the new product permits a
clean application initialization; that authorization is not permission to destroy
unrelated/private data during a machine move.

## Receiving-machine acceptance

Before further product edits:

1. Confirm source HEAD, dirty/untracked files and deliberate deletions survived.
2. Compare original Markdown/PDF hashes with [the entry document](README.md).
3. Read transferred `AGENTS.md` and reviewed plans.
4. Run planning verification and repository policies without modifying fingerprints.
5. Identify new paths, ports, Docker context, storage roots and private settings.
6. Rebuild the isolated reference, then reproduce recorded failures before claiming
   them fixed. Fresh credentials/fixtures are preferable to replaying old sessions.

The source machine's old logs can contain absolute macOS paths. Use the matching
relative artifact directory after relocation; do not rewrite the historical logs
to imply they ran on the new machine.
