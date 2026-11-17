# Event catalog

Status: DRAFT

Envelope and delivery rules: [communication and events](../../04-architecture/communication-and-events.md). Ordering is per `subject_id`. All payloads are IDs + minimum data.

| Event | v | Producer | Consumers | Payload (summary) | Meaning |
|---|---|---|---|---|---|
| `AccountInvited` | 1 | identity | access, notify | account_id, language | an invite exists |
| `AccountActivated` | 1 | identity | access, library, notify | account_id | password set |
| `AccountSuspended` / `Reactivated` / `Disabled` | 1 | identity | access, library, gateway cache | account_id | status change |
| `PasswordLinkIssued` | 1 | identity | notify | account_id, link_ref, purpose, language | send a link (secret by reference) |
| `SessionRevoked` | 1 | identity | gateway cache | session_id? / account_id | invalidate cached assertions |
| `GrantChanged` | 1 | access | library (cache), gateway (cache) | account_id, action, target, change | invalidate decision caches |
| `DefaultPolicyChanged` | 1 | access | caches | policy_revision | |
| `OpeningConsumed` | 1 | access | library | account_id, book_id | audit/analytics |
| `BookDraftUpserted` | 1 | catalog | ingestion | book_id, source_key, revision | saga step 1 done |
| `BookPublished` | 1 | catalog | content, access, library, search (self), ingestion | book_id, artifact_set_id, revision | visible to public |
| `BookArchived` | 1 | catalog | content, library, search | book_id | hidden |
| `BookMetadataChanged` | 1 | catalog | access (book_facts), library (book_ref), search | book_id, changed_fields | |
| `AgentMerged` / `AgentSplit` | 1 | catalog | search, ingestion | from, into | |
| `ArtifactSetSealed` | 1 | content | catalog, ingestion | book_id, artifact_set_id, doc_hash | build complete |
| `ArtifactSetActivated` | 1 | content | library | book_id, artifact_set_id, previous | trigger re-anchor |
| `AnnotationReanchorDone` | 1 | library | content | book_id, artifact_set_id | retention may release |
| `JobStateChanged` | 1 | ingestion | web (SSE bridge) | job_id, state, step | UI |
| `ReviewRequested` | 1 | ingestion | web, notify (admin digest) | review_id, kind | |
| `JobFailed` | 1 | ingestion | notify | job_id, reason_code | |
| `SourceDriftDetected` | 1 | ingestion | notify | source_id, fingerprint | |
| `KindleRequested` | 1 | library | notify | request_id, owner_id, book_id, address_ref | |
| `KindleSent` / `KindleFailed` | 1 | notify | library | request_id, ... | |
| `MailSent` / `MailFailed` | 1 | notify | ingestion/identity (optional dashboards) | delivery_id, kind | |

Rule: a new event or consumer requires a row here and, if it changes state in the consumer, an idempotency key definition.
