# Entities — recognition, resolution, duplicates

Status: DRAFT

## 1. What is extracted

| Entity | Typical forms in the source | Output |
|---|---|---|
| Title / subtitle / original title / volume | page `<title>` "Title – Author", title page lines, `মূল:` | `DisplayText` + evidence |
| Writer, translator, editor, compiler, illustrator, cover artist | `লেখক`, `অনুবাদ ও সম্পাদনা – ফারুক হোসেন`, `ভাষান্তর`, `সংকলক`; slash/dash lists; byline in title | `Credit{role, raw, candidates[]}` (many roles per person allowed) |
| Publisher, address | `প্রকাশক`, `প্রকাশনী`, address words, city names | `Org` + `address?` |
| Edition / first published / date | `প্রথম প্রকাশ`, `সংস্করণ`, month names, years (Bengali/ASCII digits) | normalized date or text |
| Series, category, language, page count, price, ISBN | KV pairs, source terms (`entry-terms-series/category`), detection | typed fields |
| Dedication | per classification | text |

## 2. Recognition pipeline

1. **Segment** the Book-Info candidates into *fragments*: split on newlines/`<br>`, ` / `, ` – `, `।` (danda) only when a fragment boundary also has a label word.
2. **Label detect**: match known labels (versioned alias table per field; Bengali + English; spacing/diacritic variants) with longest-match; a fragment `label SEP value` is a KV. Role words may combine (`অনুবাদ ও সম্পাদনা`) → multiple roles.
3. **Positional KV** (no label): the legacy ordered form "title / series / author / translator and editor" is parsed by an ordered template set (ruleset) with each template carrying prior probability; template choice must be unambiguous or goes to review.
4. **Value split**: multiple values split on `,`, `ও`, `এবং`, `&`, ` and ` only inside a person-list context (not inside titles).
5. **Name recognition (positive, not only negative)**: a candidate is a `PersonName` when it matches the name grammar: optional honorific (`ড.`, `সৈয়দ`, `মোহাম্মদ`…), 1–4 name tokens from/like the name lexicon or capitalized Latin tokens, initials allowed (`জে. কে. রাউলিং`), no verb morphology, no sentence punctuation, not in `NonPerson` lexicons (months, cities, topic words, role words). Each rule contributes a score (the legacy negative rules become **features**, not hard vetoes) → `Confidence`.
6. **Organization recognition**: publisher keywords (`প্রকাশনী`, `পাবলিকেশন্স`, `Press`, `Books`…) raise org score; address fragments are split off by address lexicon + digits + separators (`,`).
7. **Dates**: parse Bengali/ASCII digits; Bengali month names; ranges; ambiguous → keep as text.

Every output item: `{value, kind, role?, evidence: [BlockId…], rule_ids, confidence}`.

## 3. Resolution to catalog Agents (read-only query + review)

For each person/org candidate, `catalog.resolve(candidate)` returns scored matches:

| Match tier | Condition | Action |
|---|---|---|
| T1 exact | `exact_key` equals an Agent's name or alias | auto-link (confidence 1.0) |
| T2 alias | `fuzzy_key` equal (spelling-variant folding) or Latin alias match | auto-link if single candidate and corroborated (shares a series/publisher/known co-credit) else review |
| T3 near | token-set Jaccard ≥ 0.85 or edit ratio ≥ 0.9 on `fuzzy_key` | **never auto-link**; review with candidates |
| T4 none | no match | propose **new Agent** — auto-create only when confidence ≥ create-threshold and the name is syntactically a clean full name; else review |

Rules: ingestion never merges or edits existing agents; it only links or proposes. New aliases discovered (e.g. a new spelling) are proposed with evidence for curator approval. Names are never identity keys (INV-CAT-005).

## 4. Work / translation / edition model and the five-case policy

Key tuple: `K = (title_key, writers[], translators[], publisher, edition_label, language)` (normalized; `title_key` = exact key plus fuzzy key). Decision function (pure; INV-CAT-006, INV-ING-015):

```
classify(incoming I, existing candidates C) → Outcome:
  1. no candidate with title match (exact or fuzzy ≥ τ_title) → NewWork
  2. candidate has same title, writers disjoint (both non-empty)         → NewWork        (case 1: same title, different books)
  3. same title ∧ writers overlap (≥ 1):
        translators both non-empty ∧ disjoint                          → NewTranslation (case 3: different translators = separate books, same Work)
        else publishers both known ∧ different                         → NewEdition     (case 2: different publisher = separate book, same Work)
        else (publisher same or unknown-on-one-side)
              edition labels both known ∧ different                    → NewEdition     (case 4: offer "create as new edition")
              edition labels equal or both empty ∧ publisher same      → ExactDuplicate (refuse; link source URL as alias)
        else → NeedsReview
  4. writers unknown on either side                                    → NeedsReview     (legacy: "refuse to merge on missing authorship")
  5. title fuzzy-only match (not exact)                                → NeedsReview
```
Case 5 in the legacy spec ("all other combinations") is the `NeedsReview` fallthrough — never a silent merge. Outcomes drive: `NewEdition/NewTranslation` → create Book under the existing Work (creating the `BookGroup` linkage via catalog); `NewWork` → new Work; `ExactDuplicate` → no new book, job completes as `Duplicate`; `NeedsReview` → review item with side-by-side evidence.

The legacy three divergent matchers collapse into this one function in `domain-entities`, queried via `catalog.classify` (catalog supplies candidates via an indexed lookup, not a table scan).

## 5. Catalog hints vs page facts

Archive-listing text is the weakest source, the book page `<title>`/terms stronger, the in-book title page strongest. Conflicts are recorded as evidence with precedence `title_page > book_page_terms > archive_hint`; disagreement above a threshold becomes `LowConfidenceEntity` review.

## 6. Measures (gold)

Per-field precision/recall/F1 for each role, publisher, edition, date; agent-resolution accuracy; duplicate-policy accuracy on labeled pairs. Targets: [G-3](../../../00-charter/goals-and-non-goals.md).
