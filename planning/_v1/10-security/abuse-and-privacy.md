# Abuse resistance and privacy

Status: DRAFT

## Abuse controls

| Surface | Control |
|---|---|
| Anonymous search/browse | token-bucket rate limits per IP, page-size and window caps, cache, bot user-agent rules, optional proof-of-work/captcha switch for sustained abuse (off by default) |
| Login/reset | per-account and per-IP throttle, uniform responses, lockout is soft (delay) to avoid account-lock DoS |
| Preview scraping | preview contains only the allow-list excerpt; per-IP preview rate lower than search; canary strings detect external republication |
| Downloads | Download grant required; per-account daily cap (configurable); audit of downloads |
| Kindle | per-account daily cap; address verification |
| Uploads | admin only; size/zip limits; sandboxed parse |
| Admin | MFA, audit, rate limits on bulk operations |

## Privacy

| Data | Purpose | Retention | Rights |
|---|---|---|---|
| Account email, name | authentication, mail | until deletion | export, correct, delete |
| Reading progress, highlights, notes, shelf | the feature | until deletion by owner/account | export (Markdown/JSON), delete |
| Reading sessions | read-once, concurrency | 90 d then aggregated | — |
| IP address / user agent | security, rate limits | 30 d (hashed/prefix after 7 d) | — |
| Audit log | accountability | 2 y | admin only |
| Mail log | delivery diagnostics | 90 d, addresses hashed | — |

Principles: collect the minimum; no third-party analytics scripts in v1 (self-hosted, cookie-less, aggregate-only metrics if any); account deletion emits an event consumed by every service and completes within 7 days; no personal data in logs beyond hashed subject ids.
