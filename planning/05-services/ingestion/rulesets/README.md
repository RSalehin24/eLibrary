# Rulesets and promotion gates

Status: DRAFT

All interpretation knowledge (lexicons, label aliases, templates, thresholds, chrome phrases, normalizer settings) lives in versioned, immutable **rulesets**, never inline in code. This makes "what changed?" answerable and "did it get worse?" measurable.

## Layout

```
rulesets/<semver>/
  ruleset.toml            version, normalizer_version, thresholds, feature flags (expand_subchapters, …)
  lexicons/*.txt          roles, publishers, addresses, honorifics, month names, non-person words, front-heading names, dedication markers, chrome phrases
  templates/*.toml        positional book-info templates with priors
  labels_bn.toml, labels_en.toml
  rules/*.md              one doc per rule_id: intent, examples (positive/negative) — each example is a unit test
  CHANGELOG.md
```

Rules reference lexicons by name; the build embeds a hash of the directory (`ruleset.hash`). A job records `(ruleset_version, hash)`; a document is reproducible from `(snapshot, ruleset)`.

## Promotion workflow

```
edit on branch ──► CI: unit tests of every rule example
              └─► gold run (all gold books; stages 2–6) ─► GoldReport
GoldReport vs promoted ruleset:
   every metric ≥ promoted − 0   (no regression; ε = 0, INV-ING-011)
   conservation = 100%, determinism = 100%, epubcheck errors = 0
Candidate ─► shadow reprocess of published books ─► diff summary (counts by change type) reviewed by curator
          ─► Promote (tag, immutable) ─► new jobs use it; reprocess is explicit, never automatic
```

## Metrics (gold, per ruleset)

| Metric | Target |
|---|---|
| Structure exact-match (Type A) | ≥ 98% of books; 100% of canary shapes |
| Chapter-boundary F1 (Type B) | ≥ 0.95 |
| Writer / translator / editor F1 | ≥ 0.97 each |
| Publisher F1 | ≥ 0.95 |
| Edition/date field accuracy | ≥ 0.95 |
| Dedication detection F1 | ≥ 0.98 |
| Front-section presence accuracy (no phantom preambles) | ≥ 0.98 |
| Duplicate-policy accuracy (labeled pairs) | 100% on defined cases; NeedsReview rate reported |
| Review rate (items per book) | reported; target ≤ 0.15 after first ruleset |
| Conservation / determinism / epubcheck | 100% |

Targets are provisional until the first gold baseline (G6 reports actuals and adjusts via ADR).

## Governance

- A rule without an example is rejected in review.
- Removing a lexicon entry requires a gold run showing no regression.
- Emergency hotfix rulesets follow the same gates; the gate runtime is minutes (pure functions), so there is no shortcut.
