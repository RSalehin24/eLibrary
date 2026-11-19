# ADR-0006 — Signed, short-lived capabilities for protected bytes

Status: SUPERSEDED

Superseded by [ADR-0023](0023-reader-renders-whole-book.md) (reading tickets issued by the reader, verified by asking identity each time, D-37) and [ADR-0026](0026-gateway-auth-check-via-identity.md). `access` and `content` no longer exist.

## Context
Content must enforce "read requires an account and a grant" without calling access on every byte request, and without trusting URLs.

## Decision
`access` issues capabilities (PASETO v4.public, Ed25519) containing subject, book, artifact set, action, issued-at, expiry (≤ 300 s), and a reading-session id. `content` and `notify` verify them offline with the public key (rotatable, `kid` header). Reading sessions renew capabilities through a heartbeat that re-runs `decide`.

## Consequences
+ Content availability independent of access; revocation lag bounded by TTL (the old documented property; superseded: reading tickets are verified by identity on every redemption, so revocation is immediate, INV-RDR-007 and INV-IDN-021).
− Key management and clock-skew handling (60 s leeway, injected clock).
