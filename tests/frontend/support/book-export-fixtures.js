export function escapeCsv(value) {
  const stringValue = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(stringValue)
    ? `"${stringValue.replace(/"/g, '""')}"`
    : stringValue;
}

export function slugifyFilename(value) {
  return (
    String(value || "books-export")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "books-export"
  );
}

export function normalizeContributorName(value) {
  return (value || "").normalize("NFKC").trim().replace(/\s+/g, " ").toLowerCase();
}

export function canonicalContributorRole(value) {
  return value === "compiler" ? "editor" : value || "other";
}

export function getNormalizedContributorEntries(book) {
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

export function getContributorNamesByRole(book, role) {
  return getNormalizedContributorEntries(book)
    .filter((e) => e.role === role)
    .map((e) => e.name)
    .filter(Boolean);
}

export function getBookIdentityContributorLine(book) {
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

export function formatBookDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

export function bookTypeLabel(book) {
  return book?.record_type === "manual" ? "Manual" : "Digital";
}

export function bookExportRows(books) {
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

export function makeBook(overrides = {}) {
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

export function parseCsv(csvString) {
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

export function buildCsvString(books) {
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
