# Service-to-service and gateway authentication

Status: DRAFT

## Browser → gateway

Session cookie (opaque). The gateway resolves it through identity (cached ≤ 5 s) and
mints a **Subject Assertion**: a PASETO v4.local/public token valid 60 s containing
`subject` (Anonymous | Account{id, active, mfa_ok, demo}), `request_id`, `iat`, `exp`.
It is passed to services in the `X-Subject-Assertion` header; services accept it only
from the gateway (network policy + signature) and never read raw user headers.

## Service → service

Each call carries a **service credential**: a PASETO token signed by the calling
service key naming `iss` (caller), `aud` (callee), `exp` ≤ 60 s, and the original
subject assertion when acting on behalf of a user. Callee checks a static allow-list
`{caller → permitted routes}` (generated from the contract crates, so an unexpected
caller/route is rejected).

## Keys

| Key | Holder | Verifiers | Rotation |
|---|---|---|---|
| Gateway assertion key | gateway | all services | 90 d, overlapping `kid` |
| Service keys (one per service) | each service | peers | 90 d |
| Capability signing key | access | content, notify | 90 d, 2 active `kid`s |
| Session/TOTP encryption key | identity | identity | 180 d with re-encrypt job |

Key material is loaded from files with 0400 permissions; keys are never in env vars of
child processes or in logs ([secrets](../../10-security/secrets-and-keys.md)).

## Trust rules

1. A service never authorizes from an assertion field alone; it asks `access` (`decide`) or verifies a capability.
2. Anonymous is a valid subject — absence of an assertion is treated as Anonymous only by the gateway, never by services.
3. Internal routes are unreachable from the public edge (INV-GWY-001).
