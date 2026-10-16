/**
 * Minimal pure-JS XLSX writer for Google Docs compatibility.
 * Generates a valid .xlsx file (Office Open XML) without any dependencies.
 */

import { buildZip } from "./zip.js";
import { downloadBlob } from "./helpers";
import { formatBookDate, getContributorNamesByRole } from "../bookPresentation";

// ── XML helpers ──────────────────────────────────────────────────────────────

function escapeXml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;")
    // Strip control characters that are illegal in XML 1.0
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, "");
}

/** Convert column index (0-based) to Excel letter(s): 0→A, 25→Z, 26→AA */
function colLetter(index) {
  let letter = "";
  let n = index;
  while (n >= 0) {
    letter = String.fromCharCode((n % 26) + 65) + letter;
    n = Math.floor(n / 26) - 1;
  }
  return letter;
}

function cellRef(col, row) {
  return `${colLetter(col)}${row}`;
}

// ── Shared strings table ──────────────────────────────────────────────────────

function buildSharedStrings(allSheets) {
  const index = new Map();
  const list = [];

  function intern(value) {
    const str = String(value == null ? "" : value);
    if (!index.has(str)) {
      index.set(str, list.length);
      list.push(str);
    }
    return index.get(str);
  }

  // Pre-populate from all sheets
  for (const { rows } of allSheets) {
    for (const row of rows) {
      for (const cell of row) {
        intern(cell);
      }
    }
  }

  return { intern, list };
}

// ── Sheet XML ────────────────────────────────────────────────────────────────

function buildSheetXml(rows, sharedStrings) {
  const rowsXml = rows.map((cells, rowIdx) => {
    const r = rowIdx + 1;
    const cellsXml = cells
      .map((value, colIdx) => {
        const ref = cellRef(colIdx, r);
        const si = sharedStrings.intern(value);
        return `<c r="${ref}" t="s"><v>${si}</v></c>`;
      })
      .join("");
    return `<row r="${r}">${cellsXml}</row>`;
  });

  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>${rowsXml.join("")}</sheetData>
</worksheet>`;
}

// ── Workbook XML parts ────────────────────────────────────────────────────────

function buildSharedStringsXml(list) {
  const items = list
    .map((str) => `<si><t xml:space="preserve">${escapeXml(str)}</t></si>`)
    .join("");
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="${list.length}" uniqueCount="${list.length}">
${items}
</sst>`;
}

function buildWorkbookXml(sheetNames) {
  const sheets = sheetNames
    .map((name, i) => `<sheet name="${escapeXml(name)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`)
    .join("");
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>${sheets}</sheets>
</workbook>`;
}

function buildWorkbookRels(sheetCount) {
  const rels = Array.from({ length: sheetCount }, (_, i) =>
    `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`
  ).join("");
  const sharedStringsRel = `<Relationship Id="rId${sheetCount + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>`;
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
${rels}
${sharedStringsRel}
</Relationships>`;
}

function buildContentTypes(sheetCount) {
  const sheets = Array.from(
    { length: sheetCount },
    (_, i) =>
      `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`
  ).join("");
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
${sheets}
</Types>`;
}

const ROOT_RELS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>`;

// ── Data helpers ──────────────────────────────────────────────────────────────

const HEADERS = [
  "Book ID",
  "Title",
  "Writer(s)",
  "Translator(s)",
  "Editor(s)",
  "Publisher",
  "Category",
  "Binding",
  "Language",
  "Price",
  "Created At",
];

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

export function buildManualBookSheetRows(books) {
  return books.map((book) => [
    book.catalog_code || "",
    book.title || "",
    getContributorNamesByRole(book, "author").join(", "),
    getContributorNamesByRole(book, "translator").join(", "),
    getContributorNamesByRole(book, "editor").join(", "),
    book.publisher || book.manual_publisher || "",
    (book.categories || []).join(", "),
    bindingLabel(book.binding || book.manual_binding || ""),
    languageLabel(book.language || book.manual_language || ""),
    book.price != null && book.price !== "" ? String(book.price) : "",
    formatBookDate(book.created_at),
  ]);
}

/**
 * Group books by the given key.
 * Returns an ordered array of { label, books }.
 */
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
      // writer OR translator OR editor
      const contributors = [
        ...getContributorNamesByRole(book, "author"),
        ...getContributorNamesByRole(book, "translator"),
        ...getContributorNamesByRole(book, "editor"),
      ];
      keys = contributors.length ? contributors : [ungroupedKey];
    } else {
      keys = [ungroupedKey];
    }

    // Deduplicate keys for this book
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

/** Sanitise a string to use as a sheet/tab name (max 31 chars, no special chars) */
function safeSheetName(name, index) {
  if (!name) return `Sheet${index + 1}`;
  return name
    .replace(/[\\/:*?[\]]/g, "_")
    .substring(0, 31)
    .trim() || `Sheet${index + 1}`;
}

// ── Main export function ──────────────────────────────────────────────────────

/**
 * @param {object[]} books
 * @param {string} [groupBy]  one of: "category" | "publisher" | "binding" | "language" | "contributor" | "" | null
 * @param {string} [filename]
 */
export function exportManualBooksToExcel(books, groupBy = "", filename = "manual-books.xlsx") {
  const groups = groupBooks(books, groupBy || null);

  // Build sheet data for each group
  const allSheets = groups.map(({ label, books: groupedBooks }, i) => ({
    name: groupBy ? safeSheetName(label, i) : "Physical Books",
    rows: [HEADERS, ...buildManualBookSheetRows(groupedBooks)],
  }));

  // Build shared strings across ALL sheets
  const sharedStrings = buildSharedStrings(allSheets);

  // Build zip entries
  const files = [
    { name: "_rels/.rels", data: ROOT_RELS },
    { name: "[Content_Types].xml", data: buildContentTypes(allSheets.length) },
    { name: "xl/workbook.xml", data: buildWorkbookXml(allSheets.map((s) => s.name)) },
    { name: "xl/_rels/workbook.xml.rels", data: buildWorkbookRels(allSheets.length) },
    { name: "xl/sharedStrings.xml", data: buildSharedStringsXml(sharedStrings.list) },
    ...allSheets.map((sheet, i) => ({
      name: `xl/worksheets/sheet${i + 1}.xml`,
      data: buildSheetXml(sheet.rows, sharedStrings),
    })),
  ];

  const zipBytes = buildZip(files);
  downloadBlob(
    new Blob([zipBytes], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
    filename
  );
}
