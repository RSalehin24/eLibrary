# Complete source audit and local inference benchmark

Tasks E02/E03. Entry requires isolated engine ownership (E01). These are measured investigation deliverables with fixed output/decision rules, not assumptions that a chosen model can understand every Bengali book.

## E02: frozen inventory and evidence

1. Freeze a catalog revision with source ID/canonical URL and a manifest checksum. Include all discovered pages, linked components, contents/pagination evidence, completion classification and fetch status. New discoveries after freeze belong to the next revision; they never change an evaluation denominator mid-run.
2. Reuse valid immutable cached pages by hash. Fetch missing/changed allowed pages through the controlled source transport. Distinguish not-yet-collected, unavailable, disallowed, parse failure, and source-unfinished. Do not silently drop an entry because its text is difficult or its URL is temporarily unavailable.
3. For every work record: layout family, expected page/component set, collection coverage, hierarchy/order, front/body/back evidence, raw credits/roles, ambiguous spans/boundaries, source availability/completion, material changes, current output and discrepancies. Each reading page is independently accounted for.
4. Classify each frozen work as `understood`, `structurally_ambiguous`, `source_unavailable`, or `defective`, with reason/evidence/task. Keep source-incomplete as an independent flag. Sums of these classifications equal frozen catalog size; linked component references do not inflate book totals.
5. Build a taxonomy covering novels, continuous prose, anthologies, poetry, drama/acts/scenes, linked compilations, long unchaptered pages, nested/paginated contents, mixed credits, repeated prose, incomplete/unavailable sources and observed outliers. A one-section work is investigated, not automatically split.

The specification's census (4,171 records, 60 source-unfinished, 27,195 cached pages, 2,238 curated documents) is historical planning evidence. E02 must measure its own revision/totals. Never derive a completion percentage from those earlier numbers.

## Reference truth and split

Select 300 works spanning every observed layout and difficult case; store the selection rule, layout counts and frozen source hashes. Assign 200 to development and 100 to held-out evaluation before tuning. Related works/components/editions stay in the same split, preventing the same text from appearing as both development and held out. The grouping unit is related work/edition/component identity, not layout family: both sets cover each observed layout where enough independent works exist. Record singleton-layout limits explicitly without inventing an unseen score or moving a related work across sets.

Reference records define exact source page/block coverage, legitimate chrome exclusions, allowed chapter-boundary alternatives when objectively equivalent, reading order, front/body/back roles, bibliographic entities/roles with exact supporting spans, and relevant asset/link expectations. Engineering evaluation of this truth is outside the product UI; it creates no review queue or approval state.

Keep held-out truth separate from prompts, inference caches used for tuning, and developer fixtures. Log every held-out evaluation. When an error is investigated, preserve its original held-out result and add its regression to development; do not silently replace the case, resplit until the score passes, or report a tuned-on set as unseen. Any later unseen-generalization claim requires a newly reserved work-group-disjoint set alongside the original results. No reference case can be discarded or labelled unevaluable to close E08; use its pinned snapshots if the live source later disappears. If expected evidence for a selected reference truly cannot be established, keep the affected acceptance requirement unresolved and report it, without weakening the 300-work gate.

## E03: model/runtime and execution policy

The specification proposes Qwen3-4B GGUF Q4_K_M served privately through llama.cpp. This remains a benchmark candidate. Before installing, obtain any dependency approval required by AGENTS.md, record exact model/runtime revisions, license, artifact sizes and SHA-256, and verify local runtime compatibility. Never download “latest” then claim a pinned result. No new package/model/runtime is installed by this documentation change.

Start with one inference worker, context window 4,096 tokens, at most 1,024 response tokens, deterministic decoding, and structured schema-constrained output. Pin the exact runtime flags, seed and prompt/schema versions that actually exist in the approved runtime; verify them against that pinned runtime before use. A long work is chunked at source-block boundaries with neighboring overlap and a carried outline; no block is truncated or skipped to fit. Use page/component provenance in every chunk.

Count the complete request with the pinned model's tokenizer: system instructions, response schema, source context, carried outline and reserved response must total at most 4,096. Input therefore never exceeds 3,072 tokens; overlap and outline are part of that budget, not additional capacity. Bound overlap to 256 tokens per neighboring side and outline to 256 tokens; shrink the number of decisions/source spans per call first. If one source block is larger than the remaining input budget, use source-mapped subspans at safe text boundaries for inference only. Their original block ID and exact character ranges remain intact; they are not invented canonical chapter breaks. Reassemble all subspan coverage and reconcile overlap decisions before canonicalization. Contradictory boundaries/roles use bounded ambiguity recovery, never last-response-wins.

Decision schema v1 is `{schema_version, source_revision, chunk_id, decisions}` with at most 32 decisions per response. Each decision is a tagged structural-boundary, section-role, bibliographic-role/value-span or identity-link proposal referencing existing block IDs and exact source ranges; fields allowed for its tag are explicitly schema-validated. Values are copied from the referenced source spans by deterministic code, not accepted as newly written book text. Model confidence may be recorded as a diagnostic but never replaces evidence/calibration. Split a large decision batch into fully covered calls rather than accepting a truncated response. E03 must record the pinned runtime's actual supported schema/tokenization interfaces before dependent implementation, including oversized-single-block, malformed JSON, output-limit, overlap-conflict and prompt-injection regressions.

The model only proposes labels, boundaries, roles and identity evidence using supplied source IDs/spans. It has no tool invocation, filesystem, credential, network, or publication authority. Source instructions remain quoted data; reject attempts to add executable actions, unsupported block IDs, fabricated values, rewritten prose or policy changes. Validate every response and its evidence before caching or using it.

Cache key is SHA-256 of source block hashes/order, extractor version, model checksum, runtime/configuration, prompt version and decision-schema version. A changed dependency invalidates the affected decisions, not unrelated cached collection. Malformed/truncated/inconsistent output is a typed decision failure; retry at most twice using the same bounded evidence and explicit validation feedback, then classify unresolved ambiguity without publication. Never use a paid/free-tier endpoint on failure.

## Resource preflight

Planning-time hardware was 8 GB RAM and about 12 GB free disk; measure current availability. Run one inference process at a time, off website/reader request paths. Before benchmark/full run, inventory model files, runtime, source cache and one candidate's maximum expanded/export/staging needs. Required free disk is remaining downloads + twice that candidate's bounded expansion/staging estimate + 2 GiB reserve. Recheck before each write stage. If insufficient, keep `retry_wait` with `resource_disk` and a paced resource probe; never delete unrelated files automatically.

The initial inference resident-memory ceiling is 3.5 GiB; keep at least 1 GiB host available and no swap-thrashing requirement for website/database/reader usability. Measure peak process and whole-stack memory under representative longest chunks. If the ceiling cannot be met, reduce context/chunk size only with full-coverage checks and reevaluate accuracy; if still unsuitable, leave the candidate failed and the engine gate open. Another model/runtime requires a documented, approved candidate and repeat of E03, never a silent cloud fallback.

Record host/runtime versions, cold/warm latency, peak RAM/disk, tokens and per-work time by layout/size, and source-fetch time separately. Project full frozen-catalog runtime from measured family/size groups with cache-hit assumptions and uncertainty bounds. A projection is not an executed full-catalog result. Insufficient resources expose a waiting reason and do not mark a job succeeded.

## Metrics and exit rules

- Source coverage: all expected retained blocks accounted for, exclusions evidenced; report missing/duplicate/reordered blocks per work and layout.
- Entities: precision/recall for each supported role/type/language, exact evidence validity, and false merges. Empty denominators are reported as not applicable with counts, never 100%.
- Structure: boundary precision/recall/F1, exact reading order, section roles and case-level correctness by layout/language. Continuous works have no invented boundary requirement.
- Report every known wrong, ambiguous and unavailable work individually. Expected content/order/chapters/entities for every reference and held-out case must be correct before E08. Source availability of the broader catalog is reported separately from reference correctness. Known defects cannot be waived by aggregate scores, case exclusion or changed thresholds.
- Run real local inference for E03 results. Fixture/mocked model answers can test schema/retry/security integration but cannot establish linguistic or structural correctness.

E02 exits with reconciled inventory, taxonomy and immutable split/reference manifests. E03 exits with a reproducible real benchmark, resource budget, candidate decision, errors and failure policy. A failing candidate blocks intelligent full-catalog processing; source collection/audit can still continue within its approved bounds, with no claim that engine quality passed.
