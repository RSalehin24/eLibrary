# access

Status: DRAFT

May this subject do this action to this thing? One pure answer, everywhere.

| | |
|---|---|
| Owns | grants, default-grant policy, read-once openings, capability signing keys, grant audit |
| Does not own | accounts, books, sessions |
| Requirements | REQ-ACC-001…012, REQ-IDN-007 |
| Emits | `GrantChanged`, `OpeningConsumed`, `DefaultPolicyChanged` |
| Calls | identity (`facts`) |
| Called by | catalog, library, ingestion, identity-admin routes, gateway (coarse checks) |

## The heart: `domain-access::decide`

```rust
pub struct DecisionInput<'a> { pub subject: &'a Subject, pub action: Action, pub resource: &'a ResourceFacts,
                               pub grants: &'a GrantSet, pub now: Instant }
pub fn decide(input: &DecisionInput<'_>, policy: &DefaultPolicy) -> Decision;   // ≤ 3 parameters (rule)
pub enum Decision { Allow(Allowed), Deny(DenyReason) }
```

- Pure, total, no I/O, no clock reads (INV-ACC-003/010).
- `DenyReason` is a closed enum (`Anonymous`, `Inactive`, `NoGrant`, `Expired`, `Revoked`, `ReadOnceConsumed`, `MfaRequired`, `Unpublished`, `DemoReadOnly`, `ManagementRequired`) so UI can explain and tests can assert reasons.
- Modeled in [access.als](../../03-correctness/formal-models/alloy/access.als); the same cases are replayed against the Rust function.

## Capabilities

On Allow for Read/Download/SendToKindle, access issues a `Capability` ([ADR-0006](../../04-architecture/adr/0006-capability-tokens.md)). A reading session heartbeat (`POST /reading/heartbeat`) re-decides and renews; a Deny stops renewal, so revocation takes effect within the TTL.

## Read-once

Opening consumption uses a SERIALIZABLE transaction on `(account, book)`; consumption happens when library reports `Prepared` (not at request time) — [ReadOnce](../../03-correctness/formal-models/tla/ReadOnce.tla).

See [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [tests](test-plan.md).
