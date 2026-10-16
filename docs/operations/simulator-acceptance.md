# Simulator acceptance — 16 October 2026

The user requested completion of the remaining checks and then explicitly
required **simulators only**. The checks below are complete within that scope.
No production deployment, external email, physical-device installation, or
separate-machine capacity claim is included.

| Check | Result | Evidence and scope |
| --- | --- | --- |
| HTTPS load | Passed at 1, 5, and 20 virtual users | Actual pinned k6 against isolated TLS/Nginx/API/Next; shared VM and synthetic catalog |
| Ubuntu installation | Passed | Ubuntu 24.04 container installed actual Docker/Compose packages; systemd enable/restart simulated |
| Debian installation | Passed | Debian 12 container installed actual Docker/Compose packages; systemd enable/restart simulated |
| Install/relaunch/reinstall | 12 focused browser checks passed | Chromium, Android Pixel 7, iPhone 13; OS installation signals simulated, actual application UI/worker |
| Account mail and Kindle | Passed | Loopback SMTP acceptance, EPUB attachment, fragment links, ambiguous acceptance and duplicate-send protection |
| Bengali search relevance | Passed on synthetic intents | Combined mail/search run passed 33 cases; production editorial judgment is outside simulator scope |
| Browser timing | 12 observations completed | Desktop and 4× CPU slowdown Android profile; localhost production Next frontend with development Django API |

The previous full browser matrix (108 each desktop engine and 30 each mobile
profile), 1,247 backend/tools cases, both production builds, restore/recovery
drills, and the 10,000-book disposable PostgreSQL query profile remain recorded
in the [handoff](../implementation-handoff.md). The latest continuation passed
19 Python tools checks, 18 performance helper tests, the 12 focused browser checks, and
the measured simulations. Existing 21 web helper tests, strict TypeScript,
ESLint, mypy on 199 configured source files, affected Python lint/format, shell
syntax, and repository policies pass.

## Capacity

At 20 virtual users the simulation completed 1,962 HTTP requests at 55.19
requests/second, with zero failed checks. Public p95 latency was 154.17 ms;
protected reading p95 was 42.50 ms. The catalog contained 47 records, including
26 published/approved records. See [capacity verification](capacity-verification.md)
for all three runs, actual hardware, image provenance, utilization, limitations,
and the guarded runner command.

The isolated application stack is stopped and all persistent volumes are
retained. The original foundation PostgreSQL/Redis services and local API/web
preview remain available. Artifact privacy checks found no fixture password,
session cookie, or protected-session URL in the three capacity artifact sets.

## Host installer simulations

`deploy/scripts/install-docker.sh` now selects the distribution's own Docker
repository/key URL and rejects unsupported or incomplete OS metadata before
running apt. Six regression cases cover Ubuntu, Debian, unsupported distributions,
and invalid/missing codenames.

`tests/deployment/simulate_host_install.sh` refuses execution outside an isolated
Docker container or when a host Docker socket is mounted. Both simulations
started without Docker installed, performed the real apt package installation,
and verified Docker Engine **29.9.1**, Compose **5.6.0**, Buildx, and containerd.
Only `systemctl enable docker` and `systemctl restart docker` were simulated;
no Docker daemon was started inside those containers.

The Ubuntu base was the approved Playwright Noble image; Debian used the approved
Python 3.12.15 Bookworm image. Private results/logs are under
`test-artifacts/deployment/ubuntu-install-gxj6ozke/` and
`test-artifacts/deployment/debian-install-a6kqp2ux/`. The simulator accepts the
read-only script directory at `/scripts` and a new private writable artifact
directory at `/artifacts`; set `ELIBRARY_INSTALL_SIMULATION=isolated-container`.
Do not mount the host Docker socket or use privileged mode.

The repository selection follows the publisher's
[Ubuntu](https://docs.docker.com/engine/install/ubuntu/) and
[Debian](https://docs.docker.com/engine/install/debian/) installation instructions.

## Browser and mail simulation

The new PWA journeys cover accepted install, standalone relaunch, and reinstall
after simulated removal. Native OS installation events/display mode are supplied
by `tests/web/install-simulator.mjs`; rendering, service-worker registration,
manifest checks, and application install controls execute normally. The existing
offline/update/draft-preservation journeys remain intact. Focused output:
`test-artifacts/foundation/install-simulator-browser.log`.

The loopback mail fixture accepts or disconnects after SMTP DATA, allowing the
real transport/worker to verify durable acceptance and uncertain-send handling.
It sends nothing outside the test process. Combined mail/search output:
`test-artifacts/foundation/simulator-mail-search.log` (33 passed).

## Browser lab timing

Three independent browser contexts were measured for each page/profile:

| Profile | Page | Median LCP | Median FCP | Largest observed load-window CLS |
| --- | --- | --- | --- | --- |
| Desktop | Home | 52 ms | 52 ms | 0 |
| Desktop | Catalog | 60 ms | 60 ms | 0 |
| Android, 4× CPU slowdown | Home | 104 ms | 104 ms | 0 |
| Android, 4× CPU slowdown | Catalog | 124 ms | 124 ms | 0 |

The maximum observed Event Timing duration in the catalog interactions was 56 ms.
This is a short lab session, **not a field INP percentile**. Pages used localhost,
warm servers, fresh browser contexts, and no WAN/network throttle. The collector
uses largest layout-shift session windows and excludes recent-input shifts;
four deterministic tests cover those calculations and paint/interaction data.
This follows the publisher's [LCP](https://web.dev/articles/lcp),
[CLS](https://web.dev/articles/cls), and [INP measurement](https://web.dev/articles/inp)
distinctions. Run `node tests/performance/browser_profile.mjs` with the local
preview available to generate a new private report and screenshots.

Final artifacts: `test-artifacts/performance/browser-lab-ZORQS8/summary.json`
and its twelve screenshots. The earlier `browser-lab-qEjRLS` run was superseded
after tightening the collector's first-shift session boundary regression.

## Unresolved publisher advisory

A fresh npm audit still reports five high **development-only** findings in the
Next lint chain ending at `braces` 3.0.3. The publisher has no patched release;
its [advisory discussion](https://github.com/micromatch/braces/issues/84) is closed.
No lint rule, peer check, or audit was disabled, and no incompatible framework
downgrade was applied. The production dependency audit reports zero findings.
See [verification tooling](../architecture/verification-tooling.md).
