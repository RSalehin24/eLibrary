# ADR-0006 — Signed, short-lived capabilities for protected bytes

Status: SUPERSEDED

Superseded by [ADR-0023](0023-reader-renders-whole-book.md) (reading tickets issued by the reader after an identity check) and [ADR-0024](0024-caddy-forward-auth-deny-by-default.md). `access` and `content` no longer exist.

## Context
Content must enforce "read requires an account and a grant" without calling access on every byte request, and without trusting URLs.

## Decision
`access` issues capabilities (PASETO v4.public, Ed25519) containing subject, book, artifact set, action, issued-at, expiry (≤ 300 s), and a reading-session id. `content` and `notify` verify them offline with the public key (rotatable, `kid` header). Reading sessions renew capabilities through a heartbeat that re-runs `decide`.

## Consequences
+ Content availability independent of access; revocation lag bounded by TTL (documented property, INV-ACC-008).
− Key management and clock-skew handling (60 s leeway, injected clock).
