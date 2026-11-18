# EPUB Structure Creation Pipeline — Specification

Derived from all instructions given across sessions. This document describes the **intended behaviour** of the entire EPUB ingestion, structuring, and creation pipeline.

---

## 1. EPUB Document Structure

Every generated EPUB must follow this fixed page order. Pages that have no content are **omitted entirely** — they are never added as empty pages.

| Order | Page                    | Condition                                                                                          |
| ----- | ----------------------- | -------------------------------------------------------------------------------------------------- |
| 1     | **Cover**               | Always present. Use existing cover image if available; otherwise generate a dark-mode cover image. |
| 2     | **Title Page**          | Always present.                                                                                    |
| 3     | **Book Information**    | Only if information exists.                                                                        |
| 4     | **Dedication**          | Only if a dedication is found.                                                                     |
| 5     | **Front Sections**      | Zero to many pages. Only added when actual front content exists (preface, introduction, etc.).     |
| 6     | **Table of Contents**   | Always present in every book.                                                                      |
| 7     | **Contents (chapters)** | Must exist — no book without content.                                                              |
| 8     | **End Sections**        | Zero to many pages. Only if back-matter content exists.                                            |

The EPUB internal NCX/OPF spine TOC (the epub-level toc at the front) must **not** be added — it is wrong.

---

## 2. Cover Page

- If the source site has a cover image for the book, use that image as the cover.
- If the source site has **no** cover image, generate one programmatically.
- The generated cover must:
  - Match exactly what is shown in the **dark mode** card/thumbnail on the site — same colours, same layout.
  - Display the **book title** and **author name** as text, clearly legible.
  - Be the size of a standard book cover (portrait aspect ratio).
  - Use the correct colour scheme (not a garbage/random dark colour with blue lines and no text).
- The cover is added as a **picture/image page**, not as a text title page.

---

## 3. Book Information Page (বই বিষয়ক তথ্য)

This is a **mandatory page** that must always be present.

### Content rules

- Contains **only key-value type information**. No paragraphs, no prose.
- Prose-like content from the source must never appear here.
- Field order (display in this sequence, each on its own line):
  1. Book title (শিরোনাম)
  2. Author / Writer
  3. Translator (if present)
  4. Editor (if present)
  5. Publisher
  6. Book type / genre (if present)
  7. Publishing date / edition info
  8. Publisher address
  9. Any other key-value bibliographic data found

- Format: `Key: Value` per line, or plain value lines when the key is implied by position.
- Example of correctly formatted slash-separated info that must be converted to key-value:
  ```
  থ্রি মাস্কেটিয়ার্স / কিশোর ক্লাসিক / আলেকজান্ডার দ্যুমা / অনুবাদ ও সম্পাদনা – ফারুক হোসেন
  ```
  becomes individual lines: title, series, author, translator & editor.

### Language

- For **English books**, all field labels (keys) and fixed keywords must be in **English** (e.g. "Title:", "Author:", "Publisher:").
- For Bengali books, labels may be in Bengali.
- Never write Bengali labels for an English book.

### Extraction

- Key-value info can appear anywhere in the scraped content — at the start of the first chapter, in a page titled with the book name + author, inline in intro text, etc.
- The extractor must be smart enough to identify and pull all such info out of wherever it appears, even if it is currently mixed into front content.
- If the same information already exists in the book info, it must **not** be duplicated.

---

## 4. Dedication Page (উৎসর্গ)

- Added only if a dedication exists in the source.
- If no dedication → page is omitted entirely.
- The dedication text is found under the keyword **উৎসর্গ** (or equivalent in any language).
- The dedication must be correctly identified and placed on the Dedication page — it must **never** be put inside the Preamble/Front Sections.
- Even if the scraped HTML mixes the dedication text together with other front content, the extractor must separate it out.

---

## 5. Front Sections (প্রারম্ভ / Preamble rules)

### When a Preamble / Front Section EXISTS

- Only when there is **genuinely uncategorised front content** that is:
  - Not book information (key-value facts).
  - Not a dedication (উৎসর্গ).
  - Not part of the main chapters.
  - Actually new prose/information not present elsewhere.

### When a Preamble must NOT be added

A preamble must **not** be created in these situations (all very common bugs):

1. The only content is the book title + author name (e.g. `দুজনার ঘর (গল্পগ্রন্থ) – আশুতোষ মুখোপাধ্যায়`) — this is already in Book Info, so no preamble.
2. The content is entirely key-value bibliographic info → goes to Book Info, not Preamble.
3. The content is the dedication text → goes to Dedication page, not Preamble.
4. The content duplicates information already captured elsewhere — discard it.
5. There is no genuinely uncategorised prose content at all.

### Heading detection in front sections

- An element that is `<p><strong>text</strong></p>` **counts as a heading** and must be treated as a section heading, not prose.
- Do not discard or demote these.

### Section boundary detection (Bengali only)

- The pattern `. <text> .` (a period, then text, then a period) is a **section boundary** in Bengali content.
- Only this exact pattern triggers a boundary — not `..`, `...`, `|`, or other punctuation.

### Page heading rules for front sections

- If the front section has an explicit title in the source (e.g. "ভূমিকা", "লেখকের কথা") — use that title both on the page and in the nav.
- If the content is **uncategorised prose with no explicit title** — **do not generate or display any heading on the page itself**. Just render the content as-is.
  - If there is exactly **one** such unnamed section: in the **NAV only**, use **`অন্যান্য`** (Bengali) or **`Others`** (English).
  - If there are **multiple** unnamed sections: use **`অন্যান্য 1`**, **`অন্যান্য 2`**, … (Bengali) or **`Others 1`**, **`Others 2`**, … (English) in the NAV.

### Residual / leftover front text

If text is left over after extracting book info, dedication, and sections:

- Check if it contains any **new information** not already captured.
- If no new information → discard.
- If it contains new **key-value** info → add to Book Information.
- If it contains new **prose** → include it as a Front Section page with no heading on the page; use `অন্যান্য` / `Others` in the nav (with a digit suffix if multiple such sections exist).
- Never blindly discard residual text; never blindly add it as-is with a generated heading on the page.

---

## 6. Table of Contents Page

- Every book must have exactly **one** unified TOC page.
- If the source has multiple TOC pages/sections, they must be **merged into one** unified TOC.
- The TOC contains the TOC of the **content** (chapters) only — not the front matter or end matter.
- The TOC must be correct, complete, and respect nesting.

### Plain-text TOC inside first section — drop it entirely

Some books include a TOC written as plain text (no hyperlinks) inside the first content section or front matter. This is a **printed table of contents** embedded in the text, not a navigable structure.

**Rule:** If a real linked TOC exists (entries with `/lessons/...` URLs), any plain-text TOC section must be **dropped entirely from the book** — it is not included as a page, not kept as a front section, and not merged with the real TOC. Including it would show the same information twice. The real TOC page is the only TOC.

---

## 7. NAV vs TOC — Scope Distinction

|         | NAV (sidebar/navigation)                                                                                                                          | TOC (in-book page)                              |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Covers  | Everything: Cover, Title, Book Info, Dedication, Front Sections, TOC page, all Chapters, End Sections                                             | Only the content chapters                       |
| Nesting | Must reflect nested items. If nesting is not supported, link to the parent/main topic — do not show only the nested sub-items and hide the parent | Must reflect nested items with proper hierarchy |
| Links   | Every item must have a correct working link                                                                                                       | Every item must have a correct working link     |

---

## 8. TOC and Chapter Scraping Rules

### Single-page books vs books with inherent TOC

The scraper must distinguish between two types:

**Type A — Book with an inherent TOC** (multi-chapter books on the source site):

- The source site has a TOC with linked chapters (URLs go to `/lessons/...`).
- Use this TOC exactly as-is. Do **not** generate new chapter splits from content.
- The TOC entries and hierarchy must be preserved, including nested entries.
- The parent chapter name must remain in TOC/nav — never drop it and show only its children.

**Type B — Single-page book** (entire book content on one page):

- No inherent chapter structure from the source.
- Must generate chapters, sections and a TOC from the content.
- Section boundaries in Bengali: `. <text> .` pattern.
- Headings (`<h1>`, `<h2>`, `<h3>`, `<p><strong>`) are section dividers.

### Scraping correctness

- `/books/...` cross-links on a book page are **links to other books**, not chapter links — never include them as TOC entries for the current book.
- Only `/lessons/...` URLs are actual chapter content.
- The first entry of a nested TOC must be kept as the parent — do not dive into it and discard the parent title.

### Nested TOC

- Nested TOC must be preserved in both structure and links.
- A chapter that has sub-chapters must appear in nav/toc as the parent with its sub-chapters indented beneath it.
- If the platform cannot render nesting, link the parent item to the first page of that chapter — do not show only the sub-items.

### No artificial chapter splitting

- For non-single-page books: **never** generate new chapters beyond what the source TOC has.
- Do not split introduction text on inline numbers — numbers inside introduction prose are **part of the text**, not chapter markers.
- Do not artificially separate the last heading as its own chapter if it is not listed separately in the source TOC.

### Unified TOC (multiple source TOCs)

- If a book has multiple TOC pages on the source site, merge them into one single unified TOC.
- Update NAV accordingly.

---

## 9. Chapter Content Rules

- Chapter boundaries come from the source TOC only (for multi-chapter books).
- Never split or re-organise chapter content unless it is a single-page book.
- Front items (first chapter's content) must not bleed into the front sections — they stay in the chapters.
- The last chapter is kept as-is from the source TOC — never split its last heading off as a new separate chapter.

---

## 10. End Sections

- Any back-matter content that exists after the main chapters belongs in End Sections.
- These are separate from front matter.

---

## 11. Duplication Detection

When a new book submission arrives, the system must check for duplicates considering all of the following:

1. **Same title, different books** — two books may share the same name but be entirely different works.
2. **Same title + same author, different publisher** — treat as separate books.
3. **Same title + same author, translated by different people** — treat as separate books (different translations).
4. **Same title + same author + same publisher, different edition** — offer "create as new edition" linked to the existing book group.
5. All other combinations of these dimensions must be considered.

A "create as new edition (linked to existing)" action must exist that:

- Creates a `BookGroup` linkage between the existing book and the new book being created from the submission.
- Is offered as a UI option when a probable duplicate is detected.

---

## 12. Book Information Extraction — Smart Entity Recognition

The extractor must understand that book information can appear in various formats in the scraped HTML:

- As a page whose title is the book name + author name.
- As text at the start of the first content page, formatted with `/` separators.
- As lines with `–` separators.
- As lines with `:` key-value pairs.
- As plain sequential lines (title first, then author, then publisher etc.).

All of these must be correctly parsed into structured key-value fields and placed on the Book Information page — never left in a preamble, never discarded.

---

## 13. Language-Aware Metadata

- Detect the book's language.
- For **English books**: all section labels, nav titles, TOC titles, and Book Information field keys must be in English.
- For **Bengali books**: labels may be in Bengali.
- Never output Bengali field labels (`শিরোনাম`, `লেখক`, etc.) for a book whose content is in English.

---

## 14. Reference Test Books

The following books from the source site are the canonical test set for this pipeline. Each book was used during development to identify and fix specific spec violations. Use these URLs when validating pipeline behaviour.

| Book                                    | URL                                                              | Spec Sections                                                                                                            |
| --------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| ভূমিকা — প্রফুল্ল রায়                  | https://www.example.com/books/ভূমিকা-প্রফুল্ল-রায়/       | §8 — `/books/` cross-links must not appear in TOC                                                                        |
| ২০০১ আ স্পেস ওডিসি — আর্থার ক্লার্ক     | https://www.example.com/books/২০০১-আ-স্পেস-ওডিসি-আর্থার/  | §5 — unnamed front prose kept with `অন্যান্য` nav label (no heading on page); §8 — TOC structure                         |
| শার্লক হোমস সমগ্র ১                     | https://www.example.com/books/শার্লক-হোমস-সমগ্র-১-অনুবা/  | §8 — TOC structure                                                                                                       |
| সিডনি সেলডন রচনাসমগ্র ২                 | https://www.example.com/books/সিডনি-সেলডন-রচনাসমগ্র-২/    | §8 — TOC structure                                                                                                       |
| প্রফেসর ওয়াই ৬                         | https://www.example.com/books/৪৯-প্রফেসর-ওয়াই-৬-রহস্যপু/ | §8 — TOC structure _(URL currently returns 404)_                                                                         |
| শঙ্খ ঘোষের শ্রেষ্ঠ কবিতা                | https://www.example.com/books/শঙ্খ-ঘোষের-শ্রেষ্ঠ-কবিতা/   | §7, §8 — nested TOC first entry must be preserved as parent; §3 — book info embedded in first content                    |
| স্বপ্নের বৃষ্টিমহল — ওয়াসিকা নুযহাত    | https://www.example.com/books/স্বপ্নের-বৃষ্টিমহল-ওয়া/    | §4 — dedication must not appear in front sections                                                                        |
| বাঃ ১২ — সত্যজিৎ রায়                   | https://www.example.com/books/বাঃ-১২-সত্যজিৎ-রায়/        | §7 — nested TOC must show parent name in NAV                                                                             |
| ছেড়ে আসা গ্রাম — দক্ষিণা               | https://www.example.com/books/ছেড়ে-আসা-গ্রাম-দক্ষিণা/    | §5 — spurious preamble must not be created                                                                               |
| দুজনার ঘর — আশুতোষ মুখোপাধ্যায়         | https://www.example.com/books/দুজনার-ঘর-আশুতোপাধ/         | §5 — title+author-only content must go to Book Info, not preamble                                                        |
| গল্প সমগ্র — বিভূতিভূষণ বন্দ্যোপাধ্যায় | https://www.example.com/books/গল্প-সমগ্র-বিভূতিভূষণ-বন/   | §6 — multiple TOC pages must be merged into one                                                                          |
| নির্ঝর — কাজী নজরুল ইসলাম               | https://www.example.com/books/নির্ঝর-কাজী-নজরুল-ইসলা/     | §2 — generated dark-mode cover when no image exists; §5 — no preamble when not needed                                    |
| ফ্রান্সিস সমগ্র ৪ — অনিল ভৌমিক          | https://www.example.com/books/ফ্রান্সিস-সমগ্র-৪-অনিল-ভৌ/  | §3 — front section full of book info must be converted to Book Info; §6 — multiple TOCs                                  |
| মন আয়নায় মেঘ — অর্পিতা                | https://www.example.com/books/মন-আয়নায়-মেঘ-অর্পিতা-সর/  | §4 — dedication must be extracted, not placed in preamble                                                                |
| বাউলকবি রাধারমণ গীতি সংগ্রহ             | https://www.example.com/books/বাউলকবি-রাধারমণ-গীতি-সং/    | §3, §5 — book info items must not remain in preamble                                                                     |
| রুদ্ধরাত — রবিন জামান খান               | https://www.example.com/books/রুদ্ধরাত-রবিন-জামান-খা/     | §7 — nested TOC items must not be flattened in NAV                                                                       |
| মহাপ্লাবন — অনির্বাণ বন্দ্যোপাধ্যায়    | https://www.example.com/books/মহাপ্লাবন-অনির্বাণ-বন্দ/    | §5 — front items must be extracted correctly                                                                             |
| রোল নং ১৭ — দোলা মিত্র                  | https://www.example.com/books/রোল-নং-১৭-দোলা-মিত্র-গল্পগ/ | §1 — book creation must succeed                                                                                          |
| হিমুর বাবার কথামালা — হুমায়ূন আহমেদ    | https://www.example.com/books/হিমুর-বাবার-কথামালা/        | §8, §9 — no artificial chapter splits; inline numbers are prose, not chapter markers; last heading must not be split off |
| হৃদয়ের শব্দ — ইন্দ্রনীল সেন            | https://www.example.com/books/হৃদয়ের-শব্দ-ইন্দ্রনীল-স/   | §5, §8 — `. text .` is a section boundary in Bengali; content must go to correct section                                 |
| Hamlet — William Shakespeare            | https://www.example.com/books/hamlet-william-shakespeare/ | §13 — all labels must be in English for an English book                                                                  |
| সতী — দীনেশচন্দ্র সেন                   | https://www.example.com/books/সতী-দীনেশচন্দ্র-সেন/        | §3, §12 — multi-line bibliographic info must be extracted and structured as key-value                                    |
