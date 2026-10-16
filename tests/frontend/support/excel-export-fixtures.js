export function escapeXml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;")
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, "");
}

export function bindingLabel(value) {
  if (!value) return "";
  const v = String(value).toLowerCase().replace(/[\s_-]+/g, "");
  if (v === "hardcover") return "Hardcover";
  if (v === "paperback") return "Paperback";
  return value;
}

export function languageLabel(value) {
  if (!value) return "";
  const map = { bn: "Bengali", en: "English" };
  return map[String(value).toLowerCase()] || value;
}

export function safeSheetName(name, index) {
  if (!name) return `Sheet${index + 1}`;
  return name
    .replace(/[\\/:*?[\]]/g, "_")
    .substring(0, 31)
    .trim() || `Sheet${index + 1}`;
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

export function getContributorNamesByRole(book, role) {
  return getNormalizedContributorEntries(book)
    .filter((entry) => entry.role === role)
    .map((entry) => entry.name)
    .filter(Boolean);
}

export function groupBooks(books, groupBy) {
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
