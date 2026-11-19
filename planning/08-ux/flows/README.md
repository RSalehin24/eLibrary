# Key user flows

Status: DRAFT

Each flow lists steps, the screens and service calls, and failure branches. They become the end-to-end journeys ([test strategy](../../09-testing/strategy.md)). v1 flows F1-F8 are replaced: discover-and-read is split into open-and-read and annotate; reprocess and catalog curation are covered by import, automatic publish and the Book detail Metadata tab; review, approval and grant flows are new.

| Flow | Actors | Screens |
|---|---|---|
| [Sign in with TOTP](sign-in-totp.md) | any user | [sign-in](../screens/sign-in.md) |
| [Invite acceptance](invite-acceptance.md) | admin, invitee | [users](../screens/users-access.md), [sign-in](../screens/sign-in.md) |
| [Password reset](password-reset.md) | any user | [sign-in](../screens/sign-in.md) |
| [Open and read a book](open-and-read.md) | visitor, reader | [library](../screens/library.md), [book](../screens/book-detail.md), [reader](../screens/reader.md) |
| [Annotate](annotate.md) | reader | [reader](../screens/reader.md), [notes](../screens/notes.md) |
| [Send to Kindle](send-to-kindle.md) | reader | [settings](../screens/settings.md), [book](../screens/book-detail.md) |
| [Import a book end to end](import-end-to-end.md) | operator | [import](../screens/import-workspace.md) |
| [Review a duplicate](review-duplicate.md) | operator | [import](../screens/import-workspace.md) |
| [Automatic publish](auto-publish.md) | none (operator on holds; manager after) | [catalog management](../screens/catalog-management.md), [book](../screens/book-detail.md) |
| [Grant management](grant-management.md) | admin | [users](../screens/users-access.md) |

Every flow also has the common branches: 401 returns to sign-in and back to the same place, 403 shows the reason, offline keeps form state ([states](../screens/states.md)).
