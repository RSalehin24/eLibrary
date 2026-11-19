# Accessibility

Status: DRAFT

Target: WCAG 2.2 AA (INV-WEB-003).

| Area | Requirement | Verification |
|---|---|---|
| Keyboard | All functions reachable and operable; logical tab order; skip link; reader shortcuts documented and remappable; no keyboard traps (dialogs trap focus intentionally and restore it) | Playwright keyboard journeys |
| Focus | Visible focus ring ≥ 3:1 against adjacent colors; not removed anywhere | automated + review |
| Contrast | Text 4.5:1, large text/UI 3:1 in all themes; highlight colors keep text ≥ 4.5:1 | token checker in CI |
| Semantics | Landmarks, heading hierarchy, labels, `aria-live` for toasts/job progress (polite), table headers | axe in CI (0 serious/critical), manual |
| Screen readers | NVDA+Firefox, VoiceOver+Safari, TalkBack+Chrome on the five critical journeys (search → book → preview; sign in; read; highlight; admin review resolve) | manual per release |
| Motion | `prefers-reduced-motion` honored; no autoplay | review |
| Zoom/reflow | 200% zoom and 320 CSS px reflow without horizontal scroll (except data tables with their own scroll region) | e2e |
| Targets | ≥ 44×44 px touch targets in reader and primary actions | e2e |
| Forms | Errors identified in text, linked to fields, focus moved to first error | e2e |
| Reader | Text size/theme/line-height adjustable; selection by keyboard; annotation list is navigable as text | manual |
| Language | `lang` attributes correct for bn/en runs | lint |
