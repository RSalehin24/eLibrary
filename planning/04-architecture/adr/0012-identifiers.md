# ADR-0012 — Identifiers and slugs (no catalog codes)

Status: ACCEPTED

Amended by D-36 (no structured catalog codes) and D-32 (nothing is migrated).

## Context
The legacy system had UUID primary keys, scrambled catalog codes (salted bit-mixing with check bits) and Unicode slugs. The owner decided (D-36) that books are identified by UUID and a unique slug only, and (D-32) that no legacy URLs or codes need to keep resolving.

## Decision
Internal IDs are UUIDv7 newtypes. A book's human-facing identifier is its **slug**: Unicode NFC, lowercase, hyphen-separated, unique. There are no catalog codes, no check characters and no code decoder. Former slugs of a book are kept as redirects so links created in the new system keep working. Names and titles are never identifiers.

## Consequences
+ One identifier scheme; no decoder, no two-generation coexistence.
+ Fewer places to validate (REQ and invariants for codes are dropped).
- Slug changes need the redirect table; slug uniqueness is a database constraint.
