# UX principles

Status: DRAFT

The legacy UI grew by accretion (21 pages, 10+ processing screens, 1.8k-line dark-mode override sheet). These principles are the review checklist for every screen.

1. **Reading first.** The product is books. Public pages lead with covers, titles, authors; chrome recedes. The reader is the best screen in the app.
2. **One obvious next step.** Every page has a single primary action. Anonymous visitors: *Read preview* → *Sign in to read*. Readers: *Continue reading*. Admins: the next item in their queue.
3. **Show state, never mystery.** Loading, empty, error, forbidden, offline are designed, not defaults ([page-state enum](../05-services/web/README.md)). Errors say what happened and what to do, in the reader's language.
4. **Fewer places, deeper places.** Admin ingestion has three workspaces (Sources, Jobs, Review), not ten pages; filters live in one consistent bar; bulk actions are always visible when rows are selected.
5. **Explain refusals.** A denied action shows the reason from `DenyReason` in plain language and the way forward (sign in, ask an administrator).
6. **Bengali is first-class, not translated Latin UI.** Typography, digits, line height and conjunct rendering follow the [typography guide](bangla-typography.md); layouts are tested with Bengali text lengths.
7. **Consistency by tokens, not overrides.** One design system; themes are token sets; no per-page color overrides ([design system](design-system.md)).
8. **Fast by default.** Public pages render on the server and work without JavaScript for browse/search; images have intrinsic sizes; no layout shift (CLS < 0.05).
9. **Accessible by default.** Keyboard operable, visible focus, 4.5:1 contrast, labeled controls, reduced motion, 200% zoom without loss.
10. **Reversible and safe.** Destructive actions use undo or an explicit confirm naming the object; admin diffs before apply.
11. **Honest density.** Admin screens are dense but scannable (aligned columns, sticky headers, truncation with title tooltip); public screens are spacious.

12. **One product, three form factors.** Mobile, tablet and desktop are first-class: each screen is designed for all three window classes, not shrunk from desktop ([responsive rules](design-system.md)); touch-first, keyboard-complete.

## Acceptance process (prevents the rewrite-branch trap)

- Phase exit gates G4 (public) and G5 (reader) include **owner sign-off on clickable prototypes before back-end depth is built**.
- Each screen has a one-paragraph purpose, the primary action, its states, and a link to its row in the [route map](route-map.md). A screen without these is not built.
- Visual regression snapshots (light/dark/sepia × bn/en × 360/768/1280) are approved by the owner once per redesign, then guard against drift.
