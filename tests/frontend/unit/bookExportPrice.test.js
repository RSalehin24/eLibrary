import assert from "node:assert/strict";
import test from "node:test";
import { escapeCsv, slugifyFilename, normalizeContributorName, canonicalContributorRole, getNormalizedContributorEntries, getContributorNamesByRole, getBookIdentityContributorLine, formatBookDate, bookTypeLabel, bookExportRows, makeBook, parseCsv, buildCsvString } from '../support/book-export-fixtures.js';


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
