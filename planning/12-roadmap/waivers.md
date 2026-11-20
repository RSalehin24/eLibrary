# Gate and CI waivers

Status: DRAFT

Kept from v1; the six-service rewrite adds no waiver. A waiver is a dated, owned, expiring exception (expiry at most 30 days). Expired waivers fail the plan check at the next gate. A lint suppression in code needs a matching unexpired entry here (INV-PLT-014); a function above the shape caps needs one too (INV-PLT-012, D-19).

| Date | Gate/Check | What is waived | Why | Owner | Expires | Resolution |
|---|---|---|---|---|---|---|
| 2026-11-20 | Q5 deny (licenses) | `deny.toml` allow list gains `0BSD` and `CDLA-Permissive-2.0` | `lettre` with rustls needs `quoted_printable` (0BSD) and `webpki-roots` (CDLA-Permissive-2.0); both permissive | owner | 2026-12-20 | permanent by D-103; delete this row once the plan check no longer needs it |
