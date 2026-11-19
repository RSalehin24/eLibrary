# Bengali typography guide

Status: DRAFT

Checklist for INV-WEB-004 / REQ-WEB-004, verified on a fixed sample set (conjuncts, ref/ya-phala, vowel signs, digits, mixed Latin).

| Topic | Rule |
|---|---|
| Material 3 mapping | Bengali sizes/line heights are set on the M3 type-scale tokens (display…label) for the `bn` locale; Angular Material components inherit them; do not rely on Material's default Latin-oriented ratios |
| Fonts | Reading: Noto Serif Bengali (variable) with fallback list; UI: Noto Sans Bengali; self-hosted WOFF2 subsets with `unicode-range` (Bengali block U+0980–09FF, ZWJ/ZWNJ U+200C–200D, punctuation, Latin), `font-display: swap`, preload the primary weight |
| Shaping | Never disable ligatures/conjunct features: `font-feature-settings` untouched; `font-variant-ligatures: normal`; `text-rendering: optimizeLegibility` |
| Letter-spacing | **0** for Bengali; never positive tracking (breaks conjuncts) |
| Line height | Reading 1.8 (1.7–1.9); UI 1.5; headings 1.35 — Bengali glyphs have tall matras and deep descenders |
| Size | Reading default 18 px (range 14–28); UI minimum 14 px |
| Line length | 60–75 characters; max `72ch` equivalent measured in Bengali average glyph width |
| Digits | UI chrome in Bengali digits when UI language is `bn`; **data tables, codes, exports ASCII** by default; user setting overrides; both parse on input |
| Punctuation | Danda `।` as sentence end; no space before; quotes follow language |
| Justification | Left aligned by default; `text-align: justify` optional in reader with `hyphens: none` (no Bengali hyphenation) |
| Mixed script | Latin runs wrapped with `lang="en"`; consistent baseline; font fallback metrics adjusted (`size-adjust`) to avoid jump |
| Language tags | `<html lang="bn">`, per-element `lang` for English; `dir="ltr"` |
| Selection & copy | Preserve ZWJ/ZWNJ in copy; reader highlight offsets computed on grapheme clusters, not code units |
| Truncation | Truncate at grapheme boundaries (`Intl.Segmenter`/`unicode-segmentation`), never mid-conjunct; line-clamp preferred over character cut |
| Testing | Visual snapshots for sample strings in all three themes; automated glyph-coverage test (no `.notdef`); manual review on Android, iOS, Windows, Linux Firefox/Chromium |
