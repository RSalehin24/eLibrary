# gateway - state machines

Status: DRAFT

The gateway keeps no durable state. Its three small machines are per request, per stream and per rate-limit bucket.

## Request decision (per request, REQ-GWY-002, REQ-GWY-003)

| State | Event | Guard | Next | Response |
|---|---|---|---|---|
| Received | classify | path not under `/api/<known service>/` | Rejected | 404 `not_found` |
| Received | classify | route on `PublicRoutes` | RateChecked(Public) | |
| Received | classify | otherwise | RateChecked(Protected) | |
| RateChecked | limit exceeded | | Rejected | 429 `rate_limited` + `Retry-After` |
| RateChecked(Public) | bounds ok | | Forwarding | |
| RateChecked(Protected) | identity call | reply Allow | Authorized | |
| RateChecked(Protected) | identity call | reply 401 | Rejected | 401 `unauthenticated` |
| RateChecked(Protected) | identity call | reply 403 (inactive, `mfa_incomplete`, bad CSRF) | Rejected | 403 `forbidden` / `mfa_required` / `csrf_invalid` |
| RateChecked(Protected) | identity call | timeout, error, malformed reply | Rejected | 503 `peer_unavailable` |
| Authorized | bounds ok | | Forwarding | |
| Forwarding | upstream replies | within timeout | Done | upstream status, headers stamped |
| Forwarding | upstream timeout / failure / gate full | | Rejected | 504 / 502 / 503 |

`Forwarding` is reachable only from `RateChecked(Public)` or `Authorized`. There is no transition from an identity error to `Authorized`.

## Open stream (SSE and large downloads, REQ-GWY-010, REQ-GWY-013)

| State | Event | Guard | Next |
|---|---|---|---|
| Requested | authorize ok | stream count under 20 total and 3 per user | Open |
| Requested | authorize ok | count at the limit | Closed (429) |
| Open | periodic re-authorize | Allow | Open |
| Open | periodic re-authorize | 401 / 403 (session revoked, user disabled) | Closed |
| Open | no bytes for the idle bound | | Closed |
| Open | client disconnect or upstream end | | Closed |

Closed is terminal; the slot is released in every transition to Closed.

## Rate-limit bucket (REQ-GWY-007)

| State | Event | Next |
|---|---|---|
| Absent | first request | Counting (tokens = quota - 1) |
| Counting | request, tokens left | Counting |
| Counting | request, no tokens | Limited (reply with `Retry-After`) |
| Limited | window refill | Counting |
| Counting / Limited | idle past the expiry window and table at capacity | Evicted (only non-limited first) |

## Readiness

`Ready` iff the last identity probe succeeded within the freshness bound; otherwise `NotReady`. Liveness is true while the process serves.
