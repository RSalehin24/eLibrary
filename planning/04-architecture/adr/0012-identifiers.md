# ADR-0012 — Identifiers, codes and slugs

Status: REVIEW

## Context
Legacy has UUID PKs, scrambled catalog codes (salted bit-mixing with check bits), and Unicode slugs.

## Decision
Internal IDs are UUIDv7 newtypes. Human-facing catalog codes keep their existing values (migrated) and new codes use a reversible short encoding with a check character (`sqids`-style alphabet, no ambiguous characters). Slugs are Unicode NFC, lowercase, hyphen-separated, unique; former slugs are kept as redirects forever. Names and titles are never identifiers.

## Consequences
+ Legacy URLs and codes continue to resolve (INV-MIG-002).
− Two code generations coexist; the decoder accepts both.
