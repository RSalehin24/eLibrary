import assert from "node:assert/strict";
import test from "node:test";
import { escapeXml, bindingLabel, languageLabel, safeSheetName, normalizeContributorName, canonicalContributorRole, getNormalizedContributorEntries, getContributorNamesByRole, groupBooks } from '../support/excel-export-fixtures.js';


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
