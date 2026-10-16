# Isolated platform verification — 16 October 2026

This records functional verification of the new self-hosted stack. It does not
establish the accepted capacity, device-installation, or production-launch targets.
The user explicitly approved the four base-image downloads and isolated builds/tests.

## Infrastructure

- Host: MacBookAir10,1, ARM64, eight CPU cores, 8 GiB memory.
- Colima Linux VM: two CPUs, 2 GiB memory, no swap; Docker Compose 5.1.2.
- Existing foundation PostgreSQL/Redis services retained their original volumes.
- New platform project: private database/broker/cache networks and separate volumes;
  only proxy ports 18080/18443 published for the test.
- HTTPS hostname: `library.example.test`, resolved locally by the verifier.
  A short-lived self-signed test certificate was trusted explicitly by the client;
  TLS verification was enabled. No production certificate or domain was modified.
- Runtime images: Python 3.12.15/Debian Bookworm, Node 22.23.3/Debian Bookworm,
  Nginx 1.30.6/Alpine, RabbitMQ 4.3.6, PostgreSQL 16.14, Redis 7.4.9.

All base images are pinned by digest in the Dockerfiles/Compose definition. The
review application image IDs built for this checkpoint are:

| Image | Digest |
| --- | --- |
| `elibrary-api:review` | `sha256:8ddc1a6b94dd2edd6eb6672dcb6e315142c26846f868014392ce04e1473dc5b0` |
| `elibrary-frontend:review` | `sha256:9bae7614063abb61bdb0dcc2442906b076dec9ed981c6f602d57a13551b8a39e` |
| `elibrary-proxy:review` | `sha256:f812fdd4974a479479b555eef25d9d7e4de3b707ec086c219864725b7e75d016` |

These are local review images, not a published release. Future rebuilds may have
different provenance digests. Credentials, session fixtures, certificates, dumps,
and archives remain in private ignored test directories and are omitted here.
These rebuilt images include entity/relationship administration, personal
reading/profile images, the browser fixes, regular retained Python imports,
and the final Safari installation help.

## Passed checks

`docker compose ... build` and fresh-volume initialization passed. API and frontend
readiness became healthy with read-only serving filesystems and non-root app users.
The API database role has no superuser/database-creation/role-creation privileges.

`tests/deployment/verify_platform.py` exercised the live HTTPS surface:

- Anonymous Bengali HTML and book metadata, canonical origin, JSON-LD, manifest,
  sitemaps, static script bytes, immutable caching, and uncached service-worker updates.
- Direct media/internal/legacy-route denial, authenticated chapter/download delivery,
  byte ranges, retained iframe sandbox/CSP, and reader/admin separation.
- Real preparation through database outbox, confirmed RabbitMQ publication, worker
  execution, prepared EPUB checkpoint, and repeated-command idempotency.
- New paper-book creation, private creation status, repeated creation, and reader denial.

`verify_recovery.py` passed broker stop/start, dispatch retry, repeated message
delivery, confirmed queued-message survival after broker-container replacement,
persisted stale-attempt/checkpoint recovery, Redis loss/recovery, and API/frontend
replacement through the existing proxy. During Redis loss, existing sessions and
protected book access remained available; quota-protected login returned bounded
503 responses and recovered afterward.

`verify_restore.py` passed a separate-project restore drill: it stopped writers,
captured a PostgreSQL custom dump and media/runtime archive, recorded SHA-256
checksums, restored into empty volumes, and checked sessions, permission isolation,
protected bytes/downloads, reading progress, and a paused job resumed to completion.
The source project's paused job remained unchanged. Test volumes were retained.

The VM exhausted available memory when two full stacks overlapped during the first
restore attempt. The completed drill runs one full stack at a time. This machine
is insufficient for the accepted capacity benchmark. The active interruption scenario creates a substantial valid EPUB, waits until
the worker is preparing it, sends SIGKILL to only the isolated processing worker,
and restarts it. Normal lease recovery completes the second attempt with one
ready prepared publication. Replaying duplicate messages leaves two attempts.
This passed alongside the persisted stale-heartbeat scenario.

## Reproduction and limits

The [deployment guide](platform-deployment.md) describes the configuration and test
scripts. Keep fixture files private. Test commands enforce the isolated project
prefix and test HTTPS origin and never delete persistent volumes. Restore checks
stop the source test stack while the restored stack is active, then restore the
source services. One-shot test containers may remain for inspection.

Broader verification includes 1,247 non-live backend/tools cases; 108 journeys
each in Chromium, WebKit, and Firefox; 30 each in Android/iPhone browser profiles;
21 web helper tests, 154 retained frontend unit tests, and mypy on 199 configured
source files. Strict TypeScript, ESLint, both production builds, OpenAPI validation,
migration consistency, affected Python lint/format checks, architecture policy,
and file-size policy passed. Fresh fixtures were used for each final browser project.

A clean proxy start exposed a verification race after Compose had started the
container but before HTTPS was ready. The verifier now waits for readiness with
a deadline; two deterministic startup/error regression tests passed.

The user then required simulators only. The pinned k6 image is approved/installed
and passed actual HTTPS runs at 1, 5, and 20 virtual users. Ubuntu/Debian containers
installed real Docker/Compose packages with systemd startup simulated. Installation
signals, loopback account/Kindle mail, synthetic relevance, and browser lab timing
are covered in [simulator acceptance](simulator-acceptance.md) and
[capacity verification](capacity-verification.md). Physical/staging acceptance is
outside this scope. Five development-only npm audit findings remain without a
publisher patch; the production audit has no findings.
