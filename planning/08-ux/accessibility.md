# Accessibility

Status: DRAFT

Target: WCAG 2.2 AA in both themes and the reader's sepia theme (REQ-WEB-008, 010; REQ-RDR-021).

| Area | Requirement | Verification |
|---|---|---|
| Keyboard | Every function reachable and operable; logical tab order; skip link; reader shortcuts documented; dialogs trap focus and restore it; no other traps; no hijack of browser zoom | Playwright keyboard journeys |
| Focus | Visible ring at least 3:1 against adjacent colours, never removed; focus not obscured by sticky bars | automated and review |
| Contrast | Text 4.5:1, large text and UI 3:1, light and dark and sepia; highlight colours keep text at least 4.5:1 | token checker in CI |
| Semantics | Landmarks, heading order, labelled controls, table headers; disabled controls expose a reason | axe in CI (0 serious or critical), manual |
| Live regions | Polite live regions for async results, job progress, snackbars, reader location change; errors assertive only when blocking | e2e |
| Screen readers | NVDA + Firefox, VoiceOver + Safari, TalkBack + Chrome on the critical journeys: search to book; sign in with TOTP; read; annotate; resolve a review item; grant management | manual per release |
| Motion | `prefers-reduced-motion` honoured; no autoplay; no entrance animation | review |
| Zoom and reflow | 200% text scale and 320 CSS px reflow without clipping or horizontal page scroll (data tables collapse to lists on compact) | e2e |
| Targets | At least 48 px touch targets with spacing, including reader controls | e2e |
| Forms | Errors in text, linked to the field, focus to first error; no colour-only error; password field allows paste and managers | e2e |
| Reader | Size, family, line height, margins and theme adjustable; text selection and annotate by keyboard; notes list navigable as text; Esc leaves immersive mode; location announced | manual, e2e |
| Dragging and gestures | Every swipe or tap-zone action has a button or key equivalent (WCAG 2.5.7) | e2e |
| Language | `lang` correct on `bn` and `en` runs and on book content | lint |
| Authentication | No cognitive test; TOTP field accepts paste and `autocomplete="one-time-code"` (WCAG 3.3.8) | e2e |
| Status messages | Stale or expired states (ticket, credential) are announced, not colour only | e2e |

Each [screen spec](screens/README.md) lists its own keyboard and screen-reader notes.
