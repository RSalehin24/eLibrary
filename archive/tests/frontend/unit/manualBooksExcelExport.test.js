/**
 * Unit tests for Manual Books Excel Export functionality.
 * Tests grouping, XML escaping, sheet name cleaning, and content generation.
 */

import assert from "node:assert/strict";
import test from "node:test";

// ---------------------------------------------------------------------------
// Inlined logic under test (verbatim from excel.js to match Node ESM constraints)
// ---------------------------------------------------------------------------

function escapeXml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;")
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, "");
}

function bindingLabel(value) {
  if (!value) return "";
  const v = String(value).toLowerCase().replace(/[\s_-]+/g, "");
  if (v === "hardcover") return "Hardcover";
  if (v === "paperback") return "Paperback";
  return value;
}

function languageLabel(value) {
  if (!value) return "";
  const map = { bn: "Bengali", en: "English" };
  return map[String(value).toLowerCase()] || value;
}

function safeSheetName(name, index) {
  if (!name) return `Sheet${index + 1}`;
  return name
    .replace(/[\\/:*?[\]]/g, "_")
    .substring(0, 31)
    .trim() || `Sheet${index + 1}`;
}

// Mimicking contributors helper from contributors.js
function normalizeContributorName(value) {
  return (value || "").normalize("NFKC").trim().replace(/\s+/g, " ").toLowerCase();
}

function canonicalContributorRole(value) {
  return value === "compiler" ? "editor" : value || "other";
}

function getNormalizedContributorEntries(book) {
  if (book.contributors?.length) {
    const exactSeen = new Set();
    const entries = [];
    const nonAuthorNames = new Set();

    book.contributors.forEach((entry) => {
      if (!entry?.name) return;
      const role = canonicalContributorRole(entry.role);
      const normalizedName = normalizeContributorName(entry.name);
      const contributorKey = `${normalizedName}|${role}`;
      if (!normalizedName || exactSeen.has(contributorKey)) return;
      exactSeen.add(contributorKey);
      if (role !== "author") nonAuthorNames.add(normalizedName);
      entries.push({ name: entry.name, role });
    });

    return entries.filter(
      (entry) => !(entry.role === "author" && nonAuthorNames.has(normalizeContributorName(entry.name))),
    );
  }

  if (book.authors?.length) {
    return book.authors.filter(Boolean).map((name) => ({ name, role: "author" }));
  }
  return [];
}

function getContributorNamesByRole(book, role) {
  return getNormalizedContributorEntries(book)
    .filter((entry) => entry.role === role)
    .map((entry) => entry.name)
    .filter(Boolean);
}

function groupBooks(books, groupBy) {
  if (!groupBy) return [{ label: null, books }];

  const ordered = [];
  const map = new Map();
  const ungroupedKey = "(None)";

  for (const book of books) {
    let keys = [];

    if (groupBy === "category") {
      keys = book.categories?.length ? book.categories : [ungroupedKey];
    } else if (groupBy === "publisher") {
      const pub = book.publisher || book.manual_publisher || "";
      keys = [pub || ungroupedKey];
    } else if (groupBy === "binding") {
      const raw = book.binding || book.manual_binding || "";
      keys = [bindingLabel(raw) || ungroupedKey];
    } else if (groupBy === "language") {
      const lang = book.language || book.manual_language || "";
      keys = [languageLabel(lang) || ungroupedKey];
    } else if (groupBy === "contributor") {
      const contributors = [
        ...getContributorNamesByRole(book, "author"),
        ...getContributorNamesByRole(book, "translator"),
        ...getContributorNamesByRole(book, "editor"),
      ];
      keys = contributors.length ? contributors : [ungroupedKey];
    } else {
      keys = [ungroupedKey];
    }

    const seen = new Set();
    for (const key of keys) {
      if (seen.has(key)) continue;
      seen.add(key);
      if (!map.has(key)) {
        map.set(key, []);
        ordered.push(key);
      }
      map.get(key).push(book);
    }
  }

  return ordered.map((label) => ({ label, books: map.get(label) }));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test("escapeXml escapes control characters and standard XML markup tags", () => {
  assert.equal(escapeXml("Hello & <World>"), "Hello &amp; &lt;World&gt;");
  assert.equal(escapeXml('Quote " and \''), "Quote &quot; and &apos;");
  // Test invalid XML char stripping (\x00, etc.)
  assert.equal(escapeXml("Invalid\x00Text"), "InvalidText");
});

test("bindingLabel normalizes binding formats correctly", () => {
  assert.equal(bindingLabel("hard_cover"), "Hardcover");
  assert.equal(bindingLabel("Hard Cover"), "Hardcover");
  assert.equal(bindingLabel("hardcover"), "Hardcover");
  assert.equal(bindingLabel("paperback"), "Paperback");
  assert.equal(bindingLabel("paper_back"), "Paperback");
  assert.equal(bindingLabel("Paper Back"), "Paperback");
  assert.equal(bindingLabel("Leather Bound"), "Leather Bound");
  assert.equal(bindingLabel(""), "");
});

test("languageLabel normalizes language codes", () => {
  assert.equal(languageLabel("bn"), "Bengali");
  assert.equal(languageLabel("en"), "English");
  assert.equal(languageLabel("fr"), "fr");
  assert.equal(languageLabel(""), "");
});

test("safeSheetName sanitizes characters forbidden in sheet names", () => {
  assert.equal(safeSheetName("History/Culture [Books]", 0), "History_Culture _Books_");
  assert.equal(safeSheetName("A very long name that is more than thirty-one characters", 0), "A very long name that is more t");
  assert.equal(safeSheetName("", 5), "Sheet6");
  assert.equal(safeSheetName(":", 1), "_");
});

test("groupBooks groups by category, handling books with multiple categories", () => {
  const books = [
    { title: "Book A", categories: ["Sci-Fi", "Drama"] },
    { title: "Book B", categories: ["Drama"] },
    { title: "Book C", categories: [] },
  ];

  const grouped = groupBooks(books, "category");
  assert.equal(grouped.length, 3);
  
  assert.equal(grouped[0].label, "Sci-Fi");
  assert.deepEqual(grouped[0].books.map(b => b.title), ["Book A"]);

  assert.equal(grouped[1].label, "Drama");
  assert.deepEqual(grouped[1].books.map(b => b.title), ["Book A", "Book B"]);

  assert.equal(grouped[2].label, "(None)");
  assert.deepEqual(grouped[2].books.map(b => b.title), ["Book C"]);
});

test("groupBooks groups by publisher", () => {
  const books = [
    { title: "Book A", manual_publisher: "Prothoma" },
    { title: "Book B", publisher: "Anyaprokash" },
    { title: "Book C", publisher: "" },
  ];

  const grouped = groupBooks(books, "publisher");
  assert.equal(grouped.length, 3);

  assert.equal(grouped[0].label, "Prothoma");
  assert.deepEqual(grouped[0].books.map(b => b.title), ["Book A"]);

  assert.equal(grouped[1].label, "Anyaprokash");
  assert.deepEqual(grouped[1].books.map(b => b.title), ["Book B"]);

  assert.equal(grouped[2].label, "(None)");
  assert.deepEqual(grouped[2].books.map(b => b.title), ["Book C"]);
});

test("groupBooks groups by binding, applying normalization labels", () => {
  const books = [
    { title: "Book A", manual_binding: "hard_cover" },
    { title: "Book B", binding: "Paper Back" },
    { title: "Book C", binding: "" },
  ];

  const grouped = groupBooks(books, "binding");
  assert.equal(grouped.length, 3);

  assert.equal(grouped[0].label, "Hardcover");
  assert.deepEqual(grouped[0].books.map(b => b.title), ["Book A"]);

  assert.equal(grouped[1].label, "Paperback");
  assert.deepEqual(grouped[1].books.map(b => b.title), ["Book B"]);

  assert.equal(grouped[2].label, "(None)");
  assert.deepEqual(grouped[2].books.map(b => b.title), ["Book C"]);
});

test("groupBooks groups by contributor including writers, translators, and editors", () => {
  const books = [
    {
      title: "Book A",
      contributors: [
        { name: "Humayun Ahmed", role: "author" },
        { name: "Jafar Iqbal", role: "editor" },
      ]
    },
    {
      title: "Book B",
      contributors: [
        { name: "Jafar Iqbal", role: "translator" },
      ]
    },
    {
      title: "Book C",
      contributors: []
    }
  ];

  const grouped = groupBooks(books, "contributor");
  assert.equal(grouped.length, 3);

  assert.equal(grouped[0].label, "Humayun Ahmed");
  assert.deepEqual(grouped[0].books.map(b => b.title), ["Book A"]);

  assert.equal(grouped[1].label, "Jafar Iqbal");
  assert.deepEqual(grouped[1].books.map(b => b.title), ["Book A", "Book B"]);

  assert.equal(grouped[2].label, "(None)");
  assert.deepEqual(grouped[2].books.map(b => b.title), ["Book C"]);
});

test("groupBooks groups by contributor canonicalizes compiler role to editor", () => {
  const books = [
    {
      title: "Book A",
      contributors: [
        { name: "Rafiq", role: "compiler" },
      ]
    },
  ];

  const grouped = groupBooks(books, "contributor");
  assert.equal(grouped.length, 1);
  assert.equal(grouped[0].label, "Rafiq");
  assert.deepEqual(grouped[0].books.map(b => b.title), ["Book A"]);
});

test("groupBooks groups by contributor deduplicates same name across roles", () => {
  const books = [
    {
      title: "Book A",
      contributors: [
        { name: "Kabir", role: "author" },
        { name: "Kabir", role: "author" },
      ]
    },
  ];

  const grouped = groupBooks(books, "contributor");
  assert.equal(grouped.length, 1);
  assert.equal(grouped[0].label, "Kabir");
  assert.equal(grouped[0].books.length, 1);
});

test("groupBooks groups by contributor filters author when same person is also non-author", () => {
  const books = [
    {
      title: "Book A",
      contributors: [
        { name: "Shahid", role: "author" },
        { name: "Shahid", role: "translator" },
      ]
    },
  ];

  const grouped = groupBooks(books, "contributor");
  assert.equal(grouped.length, 1);
  assert.equal(grouped[0].label, "Shahid");
  assert.deepEqual(grouped[0].books.map(b => b.title), ["Book A"]);
});

test("groupBooks groups by contributor falls back to book.authors legacy field", () => {
  const books = [
    {
      title: "Book A",
      authors: ["Rokeya"],
    },
  ];

  const grouped = groupBooks(books, "contributor");
  assert.equal(grouped.length, 1);
  assert.equal(grouped[0].label, "Rokeya");
  assert.deepEqual(grouped[0].books.map(b => b.title), ["Book A"]);
});
