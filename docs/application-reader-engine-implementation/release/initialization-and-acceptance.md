# Clean initialization, canaries, and final acceptance

Tasks REL01/REL02 follow E08. A scoped development rebuild may also be used earlier for W01/E01 after implementation is requested; the safeguards here apply every time. This planning request does not execute a reset or release.

## REL01: identify, quiesce, initialize

1. Record exact application environment, database names/roles, queue/vhost/Redis instance, storage roots and process/build IDs. Confirm fixture and preview environments are separate. Match each proposed reset target to this application; no shared/unrelated resource is inferred disposable.
2. Stop this application's API writers, worker/dispatcher/scheduler/inference and publication consumers. Verify they have stopped. Prevent old producers from repopulating removed schemas/queues. Do not reset a shared Redis/broker server or affect other applications.
3. Rebuild only identified disposable application DBs, generated files, obsolete records/checkpoints and named queues as needed. Existing product decisions permit scoped development resets; they do not permit discarding uncommitted source, credentials, user-supplied documents or unrelated files. No data-preservation migration/backup bridge is required merely for old development IDs/history.
4. Apply newly generated migration graphs to empty PostgreSQL with ordinary tooling; never hand-edit existing migrations, generated clients or lockfiles. Initialize configuration, current administrator/security setup, source identity and explicit schedules using current commands. Do not create physical inventory, type choices or review queues.
5. Start storage/DB/broker first, then website/reader/engine APIs, then dispatcher/worker, then exactly one scheduler after readiness. Keep external email/Kindle transport disabled for fixture verification; use explicit loopback SMTP configuration where delivery behavior is tested.
6. Load synthetic fixtures only in the isolated acceptance environment. User-facing preview receives real configured-source generated books through authorized intake, not E2E seed records. Do not generate uncontrolled full-catalog inference load before E03 has established the budget.

Clean release manifests identify the exact three service artifacts, contract/schema/preparation versions, migration graph and public offline-shell/asset fingerprints. A clean application test begins from this manifest and empty state; old IDs/files/accounts/annotations/progress/checkpoints do not become prerequisites.

## Canary coverage

| Canary | Required outcome |
| --- | --- |
| Normal chaptered Bengali/English source | Evidence, entities, HTML, EPUB, contents, spine, reader and automatic availability agree. |
| Continuous prose and long heading-rich page | Continuous works stay continuous; supported internal boundaries become sections without text loss. |
| Poetry/drama/anthology/linked components | Structure, order, credits, line breaks, links/assets and component completeness preserved. |
| Source-incomplete versus source-unavailable | Independent truthful classification; available verified revision can read, missing required evidence cannot be called prepared. |
| EPUB manual intake | No book-type choice or manual Publish; validated metadata/files and working reader; malformed upload recovers. |
| Active replacement and admin edit/archive | No mixed files; valid prior build stays live during candidate failure; admin overrides/archive respected. |
| Duplicate/crash/stop/lost receipt | Same durable outcome, no duplicate book/job/activation and no stale-worker publication. |
| Reader/current activity | Reflow/search/contents/Notes exact targets; new progress/annotations survive reopen and handle conflict/failure truthfully. |
| Local offline/privacy | Public shell opens a device file offline; no upload or private cache; safe update respects unsaved activity. |
| Permissions | All specified actor classes, revoked/expired grants, read-once behavior, CSRF, account isolation and admin-only edits. |

## REL02: final gate

Run the [verification strategy](../shared/verification/test-strategy.md) against immutable completed builds and isolated resources. Reconcile route/section/state, issue and previous-version capability records with current evidence. Re-run only gates affected by subsequent corrections, and reopen any accepted gate when a new relevant defect is found.

Complete realistic journeys: administrator discovery→selection→processing→automatic creation→metadata/cover edit; source update→regeneration; source fault→recovery; EPUB upload→read; reader browse/save→read→search/annotate→Notes→exact passage→resume; profile/security/password; access/invitation; schedule Run Now/history; authorized Kindle request/history with loopback delivery. Exercise failures, narrow screens, both languages and actual keyboard/touch interactions, not just route loading.

Final completion requires no unresolved identified visual/UX/functional/security defect, correct source/reference/held-out evidence, three independently operable services, clean-start correctness, and the user's visual/UX acceptance. Automated pass results do not substitute for that acceptance. If user acceptance is pending, report implementation verified to the recorded scope and acceptance pending; do not declare the entire product complete.

The report includes each requirement/issue/capability status, final behavior/destination, exact command/build/fixture/browser/source/model versions, non-overlapping result counts, rendered screenshots, clean initialization/canaries, corpus totals and unresolved reasons, resource/semantic results, and material limitations. Physical installation, external Kindle receipt and independent-machine performance remain explicitly unverified unless actually performed. Historical or overlapping checks are not fresh unique evidence.

## Failure and release recovery

Do not publish a release with a failed gate. Before cutover retain the last usable code/build/proxy configuration and current valid active publication; this is runtime rollback, not a historical-book archive. If a canary fails, stop the responsible producer, preserve bounded diagnostic evidence, fix the cause/add regression, regenerate the candidate and rerun affected gates. Never switch pointers to half-copied files, relax verification, or rebuild offline-worker artifacts underneath an acceptance run.

Incompatible disposable-schema changes recover through a scoped fresh initialization plus matching code/builds, not an unsafe down migration or resurrection of removed features. Production deployment, remote messages, commit and push require separate explicit instructions; REL02 produces a reviewable verified result before any such action.
