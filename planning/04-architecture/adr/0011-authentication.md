# ADR-0011 — Authentication design

Status: REVIEW

## Context
Invite-only accounts, password links, TOTP, demo access; legacy used Django sessions and PBKDF2.

## Decision
Server-side opaque sessions (256-bit random, SHA-256 hashed at rest), HttpOnly Secure SameSite=Lax cookie, idle 12 h / absolute 30 d, rotation on privilege change. Argon2id (m=64 MiB, t=3, p=1, calibrated in P1) for new hashes; legacy PBKDF2 verified and upgraded on login (REQ-MIG-003). TOTP per RFC 6238 (SHA-1, 6 digits, 30 s, ±1 step), secret encrypted at rest with a key from the secret store. Login throttling per account and address with uniform responses. WebAuthn is a later option (not v1).

## Consequences
+ Immediate revocation, simple model for TLA+.
− Session store lookup per request (cached 5 s by gateway, within the stated staleness bound).
