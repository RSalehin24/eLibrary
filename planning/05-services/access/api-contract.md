# access — API contract

Status: DRAFT · Source of truth: `contracts-access`

| Method & path | Auth | Purpose |
|---|---|---|
| `GET /me/abilities` | session | digest of what this subject may do (drives UI affordances; **not** authorization) |
| `GET/POST /admin/grants`, `GET/PATCH/DELETE /admin/grants/{id}` | `ManageAccess` | list/create/update/revoke grants; DELETE = revoke (soft) |
| `GET/PUT /admin/default-policy` | `ManageAccess` | view/replace default grants (revisioned) |
| `GET /admin/access/references` | `ManageAccess` | actions, targets for pickers |
| `POST /reading/heartbeat` | session | renew capability for an open reading session |

## Internal

| Route | Caller | Request → Response |
|---|---|---|
| `POST /internal/decide` | catalog, library, ingestion | `{subject, action, resource}` → `Allow{witness}` or `Deny{reason}`; resource facts supplied by the caller where authoritative (e.g. library knows ownership) |
| `POST /internal/capabilities` | library | `{subject, book, artifact_set, action, session_id}` → capability (only after an Allow) |
| `POST /internal/openings/consume` | library | `{account, book, session_id}` → consumed \| already_consumed_by_this_session \| denied |
| `GET /internal/keys` | content, notify | public keys with `kid` |
| `GET /internal/contract` | all | handshake |

## Guarantees

- `/internal/decide` is a pure read; same inputs ⇒ same output (modulo time and grant changes).
- Clients cache `Allow` for ≤ 5 s and **never** cache `Deny` longer than 1 s.
- Unknown action/target in a request is a typed `422`, never an implicit Deny.
