# gateway - test plan

Status: DRAFT

Levels: unit, type (compile-fail), prop, fuzz, e2e (Compose stack with stub upstreams), review.

| ID | Level | What | Maps to |
|---|---|---|---|
| TST-GWY-001 | e2e | `/internal/...`, `/api/notify/...`, `/media/...` and unknown paths return 404; no service port or volume reachable through Caddy | REQ-GWY-001, INV-GWY-001 |
| TST-GWY-002 | e2e | identity down, slow, 5xx or garbage: every protected route gives 503 and the upstream sees no request | REQ-GWY-002, INV-GWY-002 |
| TST-GWY-003 | unit | `Verdict` mapping is total: 401 vs 403 vs Allow vs error, with each deny reason | REQ-GWY-002 |
| TST-GWY-004 | type+e2e | `PublicRoutes` equals the list in REQ-IDN-014; preview and reading routes anonymous give 401 | REQ-GWY-003, INV-GWY-003 |
| TST-GWY-005 | e2e | client-supplied `X-User-Id`, scopes, request id, service token are removed; upstream sees only identity-produced values | REQ-GWY-004, INV-GWY-004 |
| TST-GWY-006 | fuzz | header names/values (case, duplicates, folding, huge) never leak or spoof an identity header; no panic | REQ-GWY-004 |
| TST-GWY-007 | e2e | mutation without CSRF, wrong CSRF, wrong `Origin`: 403 `csrf_invalid`, upstream untouched; GET unaffected | REQ-GWY-005, INV-GWY-005 |
| TST-GWY-008 | e2e+unit | request id generated, validated, propagated, returned and present in each log line | REQ-GWY-006, INV-GWY-006 |
| TST-GWY-009 | prop | rate limiter never exceeds table capacity and quota per window under random keys and times (injected clock) | REQ-GWY-007, INV-GWY-007 |
| TST-GWY-010 | e2e | anonymous and sign-in routes are limited more strictly; 429 carries `Retry-After` | REQ-GWY-007 |
| TST-GWY-011 | review+type | dependency check: no domain or storage crate; no database setting in config | REQ-GWY-008, INV-GWY-008 |
| TST-GWY-012 | e2e | CSP, HSTS, frame, referrer, content-type options on every API response, including errors (pages: **OPEN O-2**) | REQ-GWY-009, INV-GWY-009 |
| TST-GWY-013 | prop | oversize header/body (limit -1, limit, limit +1) per route class rejected; timeouts fire | REQ-GWY-010, INV-GWY-010 |
| TST-GWY-014 | e2e | a 50 MiB response streams with memory growth below the bound; per-upstream concurrency 65th call gets 503 | REQ-GWY-010 |
| TST-GWY-015 | e2e+review | gateway and Caddy configs contain no file root; file bytes appear only via upstream streams | REQ-GWY-011, INV-GWY-011 |
| TST-GWY-016 | e2e | upstream timeout 504, refusal 502, overload 503, all with the typed envelope and request id and no internals | REQ-GWY-012, INV-GWY-012 |
| TST-GWY-017 | e2e | SSE passes unbuffered; closes after session revoke and after idle; stream limits give 429 | REQ-GWY-013, INV-GWY-013 |
| TST-GWY-018 | e2e | health and readiness answer on the internal port only; readiness fails when identity is unreachable | REQ-GWY-014, INV-GWY-014 |
