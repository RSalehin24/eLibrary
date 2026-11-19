# Bengali typography guide

Status: DRAFT

Checklist for REQ-WEB-011 and REQ-WEB-012, verified on a fixed sample set (conjuncts, ref and ya-phala, vowel signs, digits, mixed Latin). Kept from v1 with the web README rules (line height 1.6-1.75 for UI) applied; reading text keeps the wider range.

| Topic | Rule |
|---|---|
| M3 mapping | Bengali sizes and line heights are set on the M3 type-scale tokens for the `bn` locale; Angular Material components inherit them |
| Fonts | UI: Noto Sans Bengali. Reading: Noto Serif Bengali (the same family embedded in built EPUBs). Self-hosted WOFF2 with `unicode-range` (Bengali block U+0980-09FF, ZWJ and ZWNJ U+200C-200D, punctuation, Latin), `font-display: swap`, preload the primary weight; Latin companion for English runs |
| Shaping | Never disable ligatures or conjunct features; `font-variant-ligatures: normal`; `text-rendering: optimizeLegibility` |
| Letter spacing | 0 for Bengali; never positive tracking; no `text-transform: uppercase` anywhere |
| Line height | UI 1.6-1.75 (body 1.7); headings 1.35-1.5; reading 1.7-1.9 (default 1.8) |
| Size | UI minimum 14 px; reading default 18 px, range 14-28 |
| Line length | 60-75 characters, reading measure capped by character width, not pixels |
| Digits | UI chrome uses Bengali digits when the UI language is `bn`; tables of identifiers, sizes, exports and URLs stay ASCII; user setting may override; both forms are accepted on input |
| Punctuation | Danda for sentence end, no space before; quotes follow the language |
| Justification | Left aligned by default; justify optional in the reader with `hyphens: none` |
| Mixed script | Latin runs carry `lang="en"`; fallback metrics adjusted with `size-adjust` to avoid jumps |
| Language tags | `<html lang>` follows the UI language; `dir="ltr"` |
| Selection and copy | ZWJ and ZWNJ preserved on copy; reader annotation offsets on grapheme clusters, not code units |
| Truncation | At grapheme boundaries (`Intl.Segmenter`), never mid-conjunct; prefer CSS line clamp |
| Sorting | Bengali collation (`Intl.Collator('bn')` on the client; catalog sorts server-side) |
| Dates and time | Zone from user or server configuration; Bengali digits and month names in `bn` |
| Testing | Visual snapshots of sample strings in light, dark and sepia; glyph-coverage test (no `.notdef`); manual review on Android, iOS, Windows, Linux |
| Copy length | Layouts are tested with Bengali strings, which run longer than English in buttons and chips; labels may wrap, never clip |
