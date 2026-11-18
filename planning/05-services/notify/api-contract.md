# notify - API contract

Status: DRAFT - source of truth: generated schema in [07-contracts](../../07-contracts/http/README.md)

notify is pull-driven; its HTTP surface is small. Public prefix `/api/notify` (scope declared per route, fail closed).

| Method and path | Scope | Request -> response | Errors |
|---|---|---|---|
| `GET /admin/mail?state&kind&after` | `manage_users` | keyset page of the delivery log (address masked, never a link) | none |
| `POST /admin/mail/{id}/retry` | `manage_users` | `failed` -> `queued`; `202` | `invalid_transition`, `not_found` |
| `GET /admin/kindle?state&after` | `manage_users` | Kindle delivery log | none |
| `POST /admin/kindle/{id}/retry` | `manage_users` | `failed` -> `queued` | `invalid_transition` |
| `GET /admin/templates`, `PUT /admin/templates/{key}/{lang}` | `manage_users` | list; replace as a new inactive version (`If-Match`) | `stale_revision`, `validation` |
| `POST /admin/templates/activate` | `manage_users` | activates a complete set (all keys in `bn` and `en`) | `incomplete_set` |
| `GET /me/kindle` | session, not demo | the caller's own Kindle history `{book_id, state, reject_reason?, at}` | none |

## Internal

| Route | Caller | Purpose |
|---|---|---|
| `GET /internal/health`, `GET /internal/contract` | all | liveness and handshake |

notify has no event inbox endpoint: it pulls `identity` and `catalog` `GET /internal/events?after=<cursor>`. It emits nothing; its log is the source for the admin pages.

## Events consumed (payloads carry ids, never addresses or links)

`email.requested{event_id, kind, user_id, language}` from identity; `kindle.requested{request_id, user_id, book_id, version, address_index}` from catalog.

## Error model

Same envelope as identity: `{ "error": { "code", "message", "request_id" } }`; `403 forbidden|forbidden_demo`, `404 not_found`, `409 invalid_transition|stale_revision`, `422 validation|incomplete_set`.
