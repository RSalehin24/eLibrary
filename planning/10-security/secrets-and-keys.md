# Secrets and keys

Status: DRAFT

| Secret | Holder | Storage | Rotation | Compromise response |
|---|---|---|---|---|
| Database passwords (per service) | service | root-only file (0400), loaded at start | 180 d | rotate + restart; audit connections |
| Gateway assertion key | gateway | file | 90 d, two active `kid`s | rotate immediately; assertions live 60 s |
| Service keys | each service | file | 90 d | rotate that service's key, peers reload |
| Capability signing key (Ed25519) | access | file | 90 d, overlap one TTL | rotate `kid` → all outstanding capabilities invalid within seconds (runbook) |
| TOTP/session encryption key | identity | file | 180 d with re-encrypt job | re-encrypt, force TOTP re-enrol if exposed |
| Source session cookie | ingestion | secret store entry, never logged | on expiry/manual | revoke at source, replace |
| Mail provider credential | notify | file | 180 d | rotate at provider |
| Backup encryption key (age) | operator | offline copy + password manager | yearly | re-encrypt backups |
| TLS certificates | proxy | ACME | automatic | — |

Rules: no secret in environment of child processes or in the repository (secret scanning in CI); config files hold *paths* to secrets; `Secret<T>` wrappers; startup fails when permissions are broader than 0400; dev uses generated throwaway keys.
