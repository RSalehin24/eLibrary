# Entities — recognition, resolution, duplicates

Status: DRAFT (reconciled with exact-key matching and the catalog-side classifier; extraction rules kept)

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

## 3. Resolution to catalog agents (read-only query plus review)

For each person or organisation candidate, ingestion calls catalog `POST /internal/agents/resolve` (internal service token) with the candidate's `exact_key` and raw text. Catalog returns scored matches; ingestion never merges or edits agents.

| Match tier | Condition | Action |
|---|---|---|
| T1 exact | `exact_key` equals an agent's name or alias `exact_key` | link (confidence 1.0) |
| T2 alias | `loose_key` equal (spelling-variant folding) or a Latin alias match | link only if there is a single candidate and it is corroborated (shared series, publisher or known co-credit); otherwise review |
| T3 near | token-set overlap on `loose_key` above the configured suggestion threshold | never auto-link; review with candidates side by side |
| T4 none | no match | propose a new agent only when the name is a syntactically clean full name and confidence is high; otherwise review |

New aliases (a new spelling) are proposed with evidence for curator approval. Names are never identity keys (INV-CAT-005). Latin and Bengali spellings of one person are connected only through catalog agent aliases.

## 4. Work, translation, edition: the duplicate policy

The single decision procedure is the staged matching in the [domain model](../domain-model.md) ("Matching rules"), run by catalog `POST /internal/duplicates/classify` over catalog rows; ingestion supplies keys and owns the review state (`duplicate_reviews`). Summary of the rules that bind this stage:

- Matching uses `exact_key` only: title key equal, then author, category, translator and publisher/edition comparison by exact-key set equality or overlap. There is no substring matching and no automatic fuzzy merge.
- Same title with disjoint authors is a different work; same title and author with different translators is a new translation; with a different publisher or edition label a new edition; all equal is an exact duplicate (refused, source URL linked, `refresh_existing` offered).
- Missing or low-confidence authors, a loose-key-only match, or a match against a soft-deleted book is `needs_review`: a human decides with side-by-side evidence. Near matches are listed, never merged.
- The decision is stored and replayed as an input on reprocess.

## 5. Catalog hints vs page facts

Archive-listing text is the weakest source, the book page `<title>`/terms stronger, the in-book title page strongest. Conflicts are recorded as evidence with precedence `title_page > book_page_terms > archive_hint`; disagreement above a threshold becomes `LowConfidenceEntity` review.

## 6. Measures (gold)

Per-field precision/recall/F1 for each role, publisher, edition, date; agent-resolution accuracy; duplicate-policy accuracy on labeled pairs. Targets: [G-3](../../../00-charter/goals-and-non-goals.md).

## 7. Marker words (correct spellings)

Role and label words are lexicon data with full vowel signs, matched as whole tokens after `exact_key`; they are never matched by substring and never stored vowel-stripped.

| Meaning | Words |
|---|---|
| Writer | লেখক, রচনা, লিখিত |
| Translator | অনুবাদক, অনুবাদ, ভাষান্তর |
| Editor | সম্পাদক, সম্পাদনা |
| Compiler | সংকলক, সংকলন |
| Adaptation | রূপান্তর |
| Original (title) | মূল |
| Publisher | প্রকাশক, প্রকাশনী |
| Edition / first published | সংস্করণ, প্রথম প্রকাশ |

Title-author splitting on a marker word (for example a page title "Title – Author", or a "মূল:" prefix) happens only when the marker is a whole token. Compound roles such as "অনুবাদ ও সম্পাদনা" yield several roles. Ordinal words (প্রথম, দ্বিতীয়, তৃতীয়) map to digits only as whole tokens, so প্রথমা is never altered. Honorifics (ডক্টর, ডঃ, ড., অধ্যাপক, জনাব, মৌলভী, মো:) go to a separate `honorific` field and never cause rejection.
