# Capacity verification

The query profile passed against a disposable PostgreSQL test database with
10,000 synthetic Bengali catalog records and contributor relationships.
Twenty requests per intent retained the four-query bound. Median request times
were 15.65–22.61 ms; p95 was 24.59–46.10 ms. The ignored
`test-artifacts/performance/discovery-profile.json` contains each query's
EXPLAIN ANALYZE/BUFFERS plan. This measures local in-process discovery requests,
not concurrent HTTPS traffic or production catalog relevance.

## HTTPS load harness

`tests/performance/capacity.mjs` is prepared for the isolated production test
origin `https://library.example.test:18443`. It exercises home/book SSR, Bengali
catalog search, and protected chapter delivery with one existing synthetic
reader identity. It launches reading once during setup and performs no progress,
editorial, mail, or background-job writes during the measured workload.

The default simulation ramps to five users, holds for twenty seconds, and ramps
down. `CAPACITY_VUS` accepts 1–1000 users. `CAPACITY_HOLD` accepts whole seconds or
minutes from `1s` through `60m`. Setup verifies authentication, CSRF data, chapter
paths, and enough session lifetime for the workload plus a completion allowance.
Public reads clear reader cookies on every iteration. Request success,
error-rate, and completed-iteration thresholds fail the run; separate
public/reading trends report median, p95, p99, maximum latency, and sample count.
Aggregate HTTP counts include the two setup requests. No latency or user-count
target has been declared satisfied by preparing this script. Independent account/session load,
large-file delivery, worker throughput, and approved latency budgets require
their own measured runs.

The approved Grafana k6 **2.3.0** image is pinned to
`sha256:9c2dee7f8ed74d317e4027c06a10f169b625638189de8d4555d0b3486a5aeb34`.
The user authorized the documented remaining checks and subsequently specified
simulators only. The image was installed and verified as k6 2.3.0 on ARM64.
JavaScript syntax and **14 dependency-free harness regression tests** passed.
They exercise the actual script with simulated k6 modules, covering successful
setup/workloads, anonymous public reads, failed requests, input/response errors,
path traversal, session expiry, duration limits, and private summary filtering.
Both the earlier summary map and the publisher's
[machine-readable schema](https://github.com/grafana/k6-summary/blob/main/schemas/summary/1.0.0/schema.json)
are covered; unknown formats fail instead of producing empty reports. These
checks do not execute k6, verify transport, or measure concurrency. The
repository's dependency-approval rule remains in force for future additions.

Run these checks without k6 or a running application:

```sh
node --experimental-vm-modules --test tests/performance/capacity.test.mjs
node --check tests/performance/capacity.mjs
```

Node's experimental VM-module flag is used only by the test double loader; the
production k6 script does not use Node APIs or import test helpers.

Run it against the guarded isolated stack with a private fixture
from `tests/deployment/compose_client.py`. Resolve the test hostname to the
application host, trust that fixture's `tls/fullchain.pem`, and keep TLS
verification enabled. Mount the fixture read-only. Supply:

- `CAPACITY_FIXTURE_PATH`: private deployment fixture JSON.
- `CAPACITY_REPORT`: a new file in an ignored writable artifact directory.
- `APPLICATION_HARDWARE`: CPU, memory, storage, OS, container limits, and replica counts.
- `LOAD_GENERATOR_HARDWARE`: a separate machine's CPU, memory, OS, and network path.

`tests/performance/run_capacity.py` automates the local simulation with the
existing isolated Compose guard. It uses the installed digest without pulling,
trusts only the test certificate, maps the test origin to the proxy's private
network address, disables transport/request logs and usage reporting, and mounts
only the fixture, public certificate, script/config, and new private report
directory. It records actual Docker hardware, image IDs, catalog counts, and
sampled container CPU/memory/I/O. Failure or timeout stops its own generator;
exit zero also requires a complete successful summary.

With the isolated proxy running:

```sh
.venv/bin/python -m tests.performance.run_capacity \
  --directory test-artifacts/deployment/isolated-yxc_0c_9 \
  --users 20 --hold-seconds 20
```

## Measured simulator results — 16 October 2026

All three HTTPS runs passed every request check and configured threshold:

| Virtual users | Hold | Requests | Requests/s | Public p95 | Reading p95 |
| --- | --- | --- | --- | --- | --- |
| 1 | 5 s | 78 | 3.75 | 57.85 ms | 26.39 ms |
| 5 | 20 s | 530 | 15.01 | 53.08 ms | 14.76 ms |
| 20 | 20 s | 1,962 | 55.19 | 154.17 ms | 42.50 ms |

The 20-user run used 47 catalog records (26 published/approved), four API
workers with four threads each, and one frontend replica. The Docker VM exposed
two CPUs and 2,055,487,488 bytes RAM. The generator shared that VM, limited to
one CPU and 256 MiB. Requests passed through TLS/Nginx over the private Docker
bridge, with one reader identity and one-second iteration think time. Async
workers/broker were stopped because this workload measures serving paths.

Private artifacts are `test-artifacts/performance/k6-d640y6qq/`,
`k6-zqj74h50/`, and `k6-c5x398d6/`. Each contains summary/provenance and sampled
utilization; the final run includes automatic hardware/corpus metadata. All
three artifact directories passed a check for fixture passwords, session cookies,
and protected-session paths. No latency budget or production user target is
declared satisfied by this small-corpus, shared-VM simulation.

Keep transport debug logging disabled and suppress the runtime's request-error
logs when running protected URLs. The summary allowlists metric names, numeric
statistics, and configured threshold outcomes, dropping URL/error tags and
unexpected fields. Requests use fixed names so session resource identifiers and
account data do not enter metrics. Verify those properties in the initial
low-load run before scaling.
Capture application CPU/memory, database/broker/cache utilization, achieved
throughput, failures, latency distributions, corpus size, and image digests.

The available Colima VM has two CPUs, about 2 GiB RAM, and no swap. The generator
contends with the application. These results verify the requested local
simulation; they do not replace a separate-machine production benchmark. The
user explicitly excluded unavailable physical/staging resources from this run.

The harness follows the publisher's documented
[setup lifecycle](https://grafana.com/docs/k6/latest/using-k6/test-lifecycle/),
[cookie jar](https://grafana.com/docs/k6/latest/javascript-api/k6-http/cookiejar/),
[system tags](https://grafana.com/docs/k6/latest/using-k6/k6-options/reference/#system-tags),
and [summary output](https://grafana.com/docs/k6/latest/results-output/end-of-test/custom-summary/).
