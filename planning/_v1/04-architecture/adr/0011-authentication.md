# ADR-0011 — Authentication design

Status: REVIEW

## Context
Invite-only accounts, password links, TOTP, demo access; legacy used Django sessions and PBKDF2.

## Decision
Server-side opaque sessions (256-bit random, SHA-256 hashed at rest), HttpOnly Secure SameSite=Lax cookie, idle 12 h / absolute 30 d, rotation on privilege change. Argon2id (m=64 MiB, t=3, p=1, calibrated in P1) for new hashes; legacy PBKDF2 verified and upgraded on login (REQ-MIG-003). TOTP per RFC 6238 (verified against the RFC text 2026-11-17): HMAC-SHA-1 and a 30 s step are the RFC defaults; 6 digits is our choice (the RFC defines no default digit count; its examples use 8; authenticator apps use 6); accept the current step plus one step of drift (the RFC recommends allowing at most one step for network delay); **reject any code whose time step was already accepted for that account** (the RFC: the verifier "MUST NOT accept the second attempt of the OTP after the successful validation"). Secret encrypted at rest with a key from the secret store. Login throttling per account and address with uniform responses. WebAuthn is a later option (not v1).

## Consequences
+ Immediate revocation, simple model for TLA+.
− Session store lookup per request (Caddy forward-auth calls identity `/internal/authorize` per request, [ADR-0024](0024-caddy-forward-auth-deny-by-default.md); a decision cache of at most 5 s is allowed).
