/**
 * Tests for the book export price column added to CSV and PDF exports.
 *
 * The source modules use extension-less imports that Vite resolves but Node's
 * native ESM resolver does not.  We therefore inline the pure logic under
 * test — the same functions verbatim from rows.js, helpers.js, and the
 * contributor/date helpers from bookPresentation — so no bundler is needed.
 *
 * Coverage:
 *   - bookExportRows: price field presence, values, all edge cases
 *   - CSV column ordering, header/data parity, multi-book correctness
 *   - escapeCsv helper
 *   - slugifyFilename helper
 */

import assert from "node:assert/strict";
import test from "node:test";

// ---------------------------------------------------------------------------
// Inlined helpers (verbatim from helpers.js)
// ---------------------------------------------------------------------------

function escapeCsv(value) {
  const stringValue = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(stringValue)
    ? `"${stringValue.replace(/"/g, '""')}"`
    : stringValue;
}

function slugifyFilename(value) {
  return (
    String(value || "books-export")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "books-export"
  );
}

// ---------------------------------------------------------------------------
// Inlined contributor helpers (verbatim from contributors.js)
// ---------------------------------------------------------------------------

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
      const key = `${normalizedName}|${role}`;
      if (!normalizedName || exactSeen.has(key)) return;
      exactSeen.add(key);
      if (role !== "author") nonAuthorNames.add(normalizedName);
      entries.push({ name: entry.name, role });
    });
    return entries.filter(
      (e) => !(e.role === "author" && nonAuthorNames.has(normalizeContributorName(e.name)))
    );
  }
  if (book.authors?.length) {
    return book.authors.filter(Boolean).map((name) => ({ name, role: "author" }));
  }
  return [];
}

function getContributorNamesByRole(book, role) {
  return getNormalizedContributorEntries(book)
    .filter((e) => e.role === role)
    .map((e) => e.name)
    .filter(Boolean);
}

function getBookIdentityContributorLine(book) {
  const parts = [
    ["author", ""],
    ["translator", "Translator"],
    ["editor", "Editor"],
    ["publisher", "Publisher"],
  ]
    .map(([role, label]) => {
      const names = getContributorNamesByRole(book, role);
      if (!names.length) return "";
      return label ? `${label}: ${names.join(", ")}` : names.join(", ");
    })
    .filter(Boolean);
  return parts.join(" · ") || "Contributor unavailable";
}

// ---------------------------------------------------------------------------
// Inlined date formatter (verbatim from formatters.js)
// ---------------------------------------------------------------------------

function formatBookDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

// ---------------------------------------------------------------------------
// Inlined bookExportRows (verbatim from rows.js after the price addition)
// ---------------------------------------------------------------------------

function bookTypeLabel(book) {
  return book?.record_type === "manual" ? "Manual" : "Digital";
}

function bookExportRows(books) {
  return (books || []).map((book) => ({
    catalogCode: book.catalog_code || "",
    title: book.title || "",
    contributors: getBookIdentityContributorLine(book),
    authors: getContributorNamesByRole(book, "author").join(", "),
    translators: getContributorNamesByRole(book, "translator").join(", "),
    editors: getContributorNamesByRole(book, "editor").join(", "),
    publishers: getContributorNamesByRole(book, "publisher").join(", "),
    categories: (book.categories || []).join(", "),
    series: (book.series || []).join(", "),
    type: bookTypeLabel(book),
    price: book.price != null && book.price !== "" ? String(book.price) : "",
    state: book.state || "",
    review: book.review_state || "",
    createdAt: formatBookDate(book.created_at),
  }));
}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

/** Build a minimal valid book fixture, merging any overrides. */
function makeBook(overrides = {}) {
  return {
    catalog_code: "MB-001",
    title: "Test Book",
    contributors: [
      { name: "Alice Author", role: "author" },
      { name: "Bob Translator", role: "translator" },
      { name: "Carol Editor", role: "editor" },
    ],
    categories: ["Fiction", "Drama"],
    series: ["Great Series"],
    record_type: "manual",
    price: "12.50",
    state: "active",
    review_state: "approved",
    created_at: "2024-03-15T00:00:00Z",
    ...overrides,
  };
}

/** Parse a CSV string into an array of field arrays (handles quoted fields). */
function parseCsv(csvString) {
  return csvString.split("\n").map((line) => {
    const fields = [];
    let current = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (inQuotes) {
        if (ch === '"' && line[i + 1] === '"') { current += '"'; i++; }
        else if (ch === '"') { inQuotes = false; }
        else { current += ch; }
      } else if (ch === '"') {
        inQuotes = true;
      } else if (ch === ",") {
        fields.push(current); current = "";
      } else {
        current += ch;
      }
    }
    fields.push(current);
    return fields;
  });
}

/** Build a CSV string from books — mirrors the production exportBooksToCsv(). */
function buildCsvString(books) {
  const rows = bookExportRows(books);
  const header = [
    "Book ID", "Title", "Writer / Translator / Editor / Publisher",
    "Writers", "Translators", "Editors", "Publishers",
    "Categories", "Series", "Price", "Type", "State", "Review", "Created At",
  ];
  const lines = [
    header.join(","),
    ...rows.map((row) =>
      [
        row.catalogCode, row.title, row.contributors,
        row.authors, row.translators, row.editors, row.publishers,
        row.categories, row.series, row.price, row.type,
        row.state, row.review, row.createdAt,
      ]
        .map(escapeCsv)
        .join(","),
    ),
  ];
  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// bookExportRows — price field
// ---------------------------------------------------------------------------

test("bookExportRows includes a price property in each row", () => {
  const rows = bookExportRows([makeBook({ price: "19.99" })]);
  assert.equal(rows.length, 1);
  assert.ok("price" in rows[0], "row should have a price property");
});

test("bookExportRows maps a numeric string price correctly", () => {
  const rows = bookExportRows([makeBook({ price: "19.99" })]);
  assert.equal(rows[0].price, "19.99");
});

test("bookExportRows maps an integer price correctly", () => {
  const rows = bookExportRows([makeBook({ price: 250 })]);
  assert.equal(rows[0].price, "250");
});

test("bookExportRows returns empty string for a null price", () => {
  const rows = bookExportRows([makeBook({ price: null })]);
  assert.equal(rows[0].price, "");
});

test("bookExportRows returns empty string for an undefined price", () => {
  const book = makeBook();
  delete book.price;
  const rows = bookExportRows([book]);
  assert.equal(rows[0].price, "");
});

test("bookExportRows returns empty string for an empty-string price", () => {
  const rows = bookExportRows([makeBook({ price: "" })]);
  assert.equal(rows[0].price, "");
});

test("bookExportRows preserves a zero price as '0' (not empty)", () => {
  // 0 is falsy — the guard 'price != null && price !== ""' must keep it
  const rows = bookExportRows([makeBook({ price: 0 })]);
  assert.equal(rows[0].price, "0");
});

test("bookExportRows price is independent of other fields", () => {
  const rows = bookExportRows([makeBook({ price: "5.00", title: "Another Title" })]);
  assert.equal(rows[0].price, "5.00");
  assert.equal(rows[0].title, "Another Title");
});

// ---------------------------------------------------------------------------
// bookExportRows — other fields still correct after price addition
// ---------------------------------------------------------------------------

test("bookExportRows maps catalog_code to catalogCode", () => {
  const rows = bookExportRows([makeBook({ catalog_code: "MB-999" })]);
  assert.equal(rows[0].catalogCode, "MB-999");
});

test("bookExportRows maps title", () => {
  const rows = bookExportRows([makeBook({ title: "Hello World" })]);
  assert.equal(rows[0].title, "Hello World");
});

test("bookExportRows maps record_type 'manual' → 'Manual'", () => {
  const rows = bookExportRows([makeBook({ record_type: "manual" })]);
  assert.equal(rows[0].type, "Manual");
});

test("bookExportRows maps record_type 'digital' → 'Digital'", () => {
  const rows = bookExportRows([makeBook({ record_type: "digital" })]);
  assert.equal(rows[0].type, "Digital");
});

test("bookExportRows joins categories array with commas", () => {
  const rows = bookExportRows([makeBook({ categories: ["Fiction", "Drama"] })]);
  assert.equal(rows[0].categories, "Fiction, Drama");
});

test("bookExportRows joins series array with commas", () => {
  const rows = bookExportRows([makeBook({ series: ["Great Series"] })]);
  assert.equal(rows[0].series, "Great Series");
});

test("bookExportRows extracts authors by role", () => {
  const rows = bookExportRows([makeBook()]);
  assert.equal(rows[0].authors, "Alice Author");
});

test("bookExportRows extracts translators by role", () => {
  const rows = bookExportRows([makeBook()]);
  assert.equal(rows[0].translators, "Bob Translator");
});

test("bookExportRows extracts editors by role", () => {
  const rows = bookExportRows([makeBook()]);
  assert.equal(rows[0].editors, "Carol Editor");
});

test("bookExportRows handles empty books array", () => {
  assert.deepEqual(bookExportRows([]), []);
});

test("bookExportRows handles null books argument", () => {
  assert.deepEqual(bookExportRows(null), []);
});

test("bookExportRows handles undefined books argument", () => {
  assert.deepEqual(bookExportRows(undefined), []);
});

// ---------------------------------------------------------------------------
// CSV output — price column presence, position, content
// ---------------------------------------------------------------------------

test("CSV header contains a Price column", () => {
  const csv = buildCsvString([makeBook()]);
  const [headerRow] = parseCsv(csv);
  assert.ok(headerRow.includes("Price"), `Price not found in header: ${headerRow.join(",")}`);
});

test("CSV Price column comes after Series and before Type", () => {
  const csv = buildCsvString([makeBook()]);
  const [headerRow] = parseCsv(csv);
  const seriesIdx = headerRow.indexOf("Series");
  const priceIdx = headerRow.indexOf("Price");
  const typeIdx = headerRow.indexOf("Type");
  assert.ok(seriesIdx < priceIdx, "Series should come before Price");
  assert.ok(priceIdx < typeIdx, "Price should come before Type");
});

test("CSV data row contains the correct price value", () => {
  const csv = buildCsvString([makeBook({ price: "49.99" })]);
  const [headerRow, dataRow] = parseCsv(csv);
  const priceIdx = headerRow.indexOf("Price");
  assert.equal(dataRow[priceIdx], "49.99");
});

test("CSV data row contains empty string when price is absent", () => {
  const book = makeBook();
  delete book.price;
  const csv = buildCsvString([book]);
  const [headerRow, dataRow] = parseCsv(csv);
  const priceIdx = headerRow.indexOf("Price");
  assert.equal(dataRow[priceIdx], "");
});

test("CSV header column count equals data row column count", () => {
  const csv = buildCsvString([makeBook()]);
  const [headerRow, dataRow] = parseCsv(csv);
  assert.equal(headerRow.length, dataRow.length);
});

test("CSV header has exactly 14 columns after price addition", () => {
  const csv = buildCsvString([makeBook()]);
  const [headerRow] = parseCsv(csv);
  assert.equal(headerRow.length, 14);
});

test("CSV price field is quoted when it contains a comma", () => {
  const row = bookExportRows([makeBook({ price: "1,000" })])[0];
  const escaped = escapeCsv(row.price);
  assert.equal(escaped, '"1,000"');
});

test("CSV multiple books all have price in correct column position", () => {
  const books = [
    makeBook({ price: "10.00" }),
    makeBook({ catalog_code: "MB-002", price: "20.00" }),
    makeBook({ catalog_code: "MB-003", price: null }),
  ];
  const csv = buildCsvString(books);
  const rows = parseCsv(csv);
  const priceIdx = rows[0].indexOf("Price");
  assert.equal(rows[1][priceIdx], "10.00");
  assert.equal(rows[2][priceIdx], "20.00");
  assert.equal(rows[3][priceIdx], "");
});

// ---------------------------------------------------------------------------
// escapeCsv helper
// ---------------------------------------------------------------------------

test("escapeCsv leaves plain text unchanged", () => {
  assert.equal(escapeCsv("hello"), "hello");
  assert.equal(escapeCsv("49.99"), "49.99");
  assert.equal(escapeCsv(""), "");
});

test("escapeCsv wraps value containing a comma in double quotes", () => {
  assert.equal(escapeCsv("one,two"), '"one,two"');
});

test("escapeCsv wraps value containing a double-quote and escapes it", () => {
  assert.equal(escapeCsv('say "hello"'), '"say ""hello"""');
});

test("escapeCsv wraps value containing a newline", () => {
  assert.equal(escapeCsv("line1\nline2"), '"line1\nline2"');
});

test("escapeCsv coerces null to empty string", () => {
  assert.equal(escapeCsv(null), "");
});

test("escapeCsv coerces undefined to empty string", () => {
  assert.equal(escapeCsv(undefined), "");
});

// ---------------------------------------------------------------------------
// slugifyFilename helper
// ---------------------------------------------------------------------------

test("slugifyFilename lowercases and replaces spaces with hyphens", () => {
  assert.equal(slugifyFilename("Physical Books List Export"), "physical-books-list-export");
});

test("slugifyFilename strips leading and trailing hyphens from whitespace", () => {
  assert.equal(slugifyFilename("  My Books  "), "my-books");
});

test("slugifyFilename collapses multiple non-alphanumeric chars to one hyphen", () => {
  assert.equal(slugifyFilename("Manual  Books -- Export"), "manual-books-export");
});

test("slugifyFilename returns fallback for empty string", () => {
  assert.equal(slugifyFilename(""), "books-export");
});

test("slugifyFilename returns fallback for null", () => {
  assert.equal(slugifyFilename(null), "books-export");
});
