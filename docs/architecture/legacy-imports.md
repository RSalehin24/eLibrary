# Retained Python imports

The retained accounts, processing, ingestion, and local seed command no longer
read Python files and execute them into a shared namespace. Their implementation
files are ordinary modules with declared imports. This includes scraper,
normalization, submissions, curation, catalog-entry inspection, account views,
processing views/services, and `seed_e2e_data`.

Small public facades re-export their existing names explicitly. The unusually
wide retained processing API delegates attribute lookup to an explicit set of
imported modules. Its public import surface remains available without executing
source text. Implementation modules reference their actual dependencies rather
than that compatibility API. A few relocated helpers preserve their former
internal module paths with bounded attribute delegation.

Processing boundaries now include catalog refresh, automation scheduling,
incomplete-catalog queries, remote-record normalization, and request advancement.
They preserve existing lifecycle, checkpoint, dispatch, and authority behavior.
Seed constants and independent fixture builders use regular imports and bound
command methods; no seed/reset command was run against existing application data.

Tests now patch the actual consumer or defining module. Existing outcome,
failure, checkpoint, and concurrency assertions remain in place. The complete
non-live backend/tools audit passed 1,247 tests, including all retained engine,
processing, and ingestion cases. Thirteen explicitly live source-network tests
were excluded. Thread-exception warnings were errors for this run.

The architecture policy now rejects runtime `exec(compile(...))` source loaders
under `app/backend/`, with regression cases for spacing variants and normal
imports. Retained test-file loaders remain outside that application-code rule.
Neither file-size exemptions nor existing lint/type rules were relaxed.
