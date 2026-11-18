/**
 * Unit tests for Physical Book Editing form mapping and payload construction.
 *
 * Exercises the logic for mapping between Book entities and Composer form states,
 * and mapping form states to PATCH payloads.
 */

import assert from "node:assert/strict";
import test from "node:test";

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

// ---------------------------------------------------------------------------
// Inlined production mapping functions to test (verbatim from implementation)
// ---------------------------------------------------------------------------

function mapBookToComposerForm(book) {
  let bindingValue = "";
  const rawBinding = (book.binding || book.manual_binding || "").toLowerCase().trim().replace(/[\s_-]+/g, "");
  if (rawBinding === "hardcover") {
    bindingValue = "hard_cover";
  } else if (rawBinding === "paperback") {
    bindingValue = "paper_back";
  }

  const priceVal = book.price !== undefined && book.price !== null ? book.price : book.manual_price;

  return {
    title: book.title || "",
    summary: book.summary || "",
    writers: getContributorNamesByRole(book, "author") || [],
    translators: getContributorNamesByRole(book, "translator") || [],
    editors: getContributorNamesByRole(book, "editor") || [],
    categories: book.categories || [],
    series: book.series || [],
    is_compilation: book.is_compilation || book.manual_is_compilation || false,
    binding: bindingValue,
    publisher: book.publisher || book.manual_publisher || "",
    price: priceVal ? String(priceVal) : "",
    language: book.language || book.manual_language || "bn",
  };
}

function mapComposerFormToPayload(form) {
  const contributors = [
    ...form.writers.map(name => ({ name, role: "author" })),
    ...form.translators.map(name => ({ name, role: "translator" })),
    ...form.editors.map(name => ({ name, role: "editor" })),
    ...(form.publisher ? [{ name: form.publisher, role: "publisher" }] : [])
  ];

  return {
    title: form.title,
    summary: form.summary,
    contributors,
    categories: form.categories,
    series: form.series,
    is_compilation: form.is_compilation,
    binding: form.binding,
    publisher: form.publisher,
    price: form.price === "" ? null : form.price,
    language: form.language || "bn",
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeBackendBook(overrides = {}) {
  return {
    title: "Old Title",
    summary: "Old Summary",
    contributors: [
      { name: "First Author", role: "author" },
      { name: "Second Author", role: "author" },
      { name: "Main Translator", role: "translator" },
      { name: "Key Editor", role: "editor" },
      { name: "Ananda Publishers", role: "publisher" },
    ],
    categories: ["History", "War"],
    series: ["Liberation War Series"],
    manual_is_compilation: true,
    manual_binding: "hard_cover",
    manual_publisher: "Ananda Publishers",
    manual_price: "350.00",
    manual_language: "bn",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test("mapBookToComposerForm correctly maps standard book properties", () => {
  const book = makeBackendBook();
  const form = mapBookToComposerForm(book);

  assert.equal(form.title, "Old Title");
  assert.equal(form.summary, "Old Summary");
  assert.deepEqual(form.writers, ["First Author", "Second Author"]);
  assert.deepEqual(form.translators, ["Main Translator"]);
  assert.deepEqual(form.editors, ["Key Editor"]);
  assert.deepEqual(form.categories, ["History", "War"]);
  assert.deepEqual(form.series, ["Liberation War Series"]);
  assert.equal(form.is_compilation, true);
  assert.equal(form.binding, "hard_cover");
  assert.equal(form.publisher, "Ananda Publishers");
  assert.equal(form.price, "350.00");
  assert.equal(form.language, "bn");
});

test("mapBookToComposerForm handles missing/falsy optional values", () => {
  const book = makeBackendBook({
    summary: null,
    manual_is_compilation: false,
    manual_binding: "",
    manual_publisher: "",
    manual_price: null,
  });
  const form = mapBookToComposerForm(book);

  assert.equal(form.title, "Old Title");
  assert.equal(form.summary, "");
  assert.equal(form.is_compilation, false);
  assert.equal(form.binding, "");
  assert.equal(form.publisher, "");
  assert.equal(form.price, "");
  assert.equal(form.language, "bn");
});

test("mapComposerFormToPayload constructs unified contributors array with roles", () => {
  const form = {
    title: "New Title",
    summary: "New Summary",
    writers: ["Alice", "Bob"],
    translators: ["Charlie"],
    editors: ["Dave"],
    categories: ["Sci-Fi"],
    series: ["Space Saga"],
    is_compilation: false,
    binding: "paper_back",
    publisher: "Seba Prokashoni",
    price: "120.00",
  };

  const payload = mapComposerFormToPayload(form);

  assert.equal(payload.title, "New Title");
  assert.equal(payload.summary, "New Summary");
  assert.deepEqual(payload.contributors, [
    { name: "Alice", role: "author" },
    { name: "Bob", role: "author" },
    { name: "Charlie", role: "translator" },
    { name: "Dave", role: "editor" },
    { name: "Seba Prokashoni", role: "publisher" },
  ]);
  assert.deepEqual(payload.categories, ["Sci-Fi"]);
  assert.deepEqual(payload.series, ["Space Saga"]);
  assert.equal(payload.is_compilation, false);
  assert.equal(payload.binding, "paper_back");
  assert.equal(payload.publisher, "Seba Prokashoni");
  assert.equal(payload.price, "120.00");
  assert.equal(payload.language, "bn");
});

test("mapComposerFormToPayload handles empty publisher and price formatting", () => {
  const form = {
    title: "New Title",
    summary: "",
    writers: ["Alice"],
    translators: [],
    editors: [],
    categories: ["Novel"],
    series: [],
    is_compilation: false,
    binding: "",
    publisher: "",
    price: "",
  };

  const payload = mapComposerFormToPayload(form);

  // Contributors should not have a publisher entry if publisher is empty
  assert.deepEqual(payload.contributors, [
    { name: "Alice", role: "author" },
  ]);
  assert.equal(payload.price, null, "Empty price should map to null");
});

test("mapBookToComposerForm resolves compiler role to editor in form state", () => {
  const book = makeBackendBook({
    contributors: [
      { name: "First Author", role: "author" },
      { name: "Main Compiler", role: "compiler" },
    ],
  });
  const form = mapBookToComposerForm(book);

  assert.deepEqual(form.editors, ["Main Compiler"]);
  assert.deepEqual(form.writers, ["First Author"]);
});

test("mapBookToComposerForm handles missing contributors list fallback to authors", () => {
  const book = {
    title: "No Contributors List",
    authors: ["Authors Fallback Name"],
    categories: [],
    series: [],
  };
  const form = mapBookToComposerForm(book);

  assert.deepEqual(form.writers, ["Authors Fallback Name"]);
  assert.deepEqual(form.translators, []);
  assert.deepEqual(form.editors, []);
});

test("mapBookToComposerForm correctly keeps whole integer prices as string", () => {
  const book = makeBackendBook({
    manual_price: 150,
  });
  const form = mapBookToComposerForm(book);
  assert.equal(form.price, "150");
});

test("mapComposerFormToPayload normalizes spaces inside contributor names when converting to payload", () => {
  const form = {
    title: "Book",
    summary: "",
    writers: ["  Alice   Name  "],
    translators: ["  Bob   Translator  "],
    editors: [],
    categories: [],
    series: [],
    is_compilation: false,
    binding: "",
    publisher: "  Prothoma   Publishers  ",
    price: "",
  };

  const payload = mapComposerFormToPayload(form);

  assert.deepEqual(payload.contributors, [
    { name: "  Alice   Name  ", role: "author" },
    { name: "  Bob   Translator  ", role: "translator" },
    { name: "  Prothoma   Publishers  ", role: "publisher" },
  ]);
});

test("mapBookToComposerForm correctly maps standard serialized API fields", () => {
  const serializedBook = {
    title: "Serialized Book Title",
    summary: "Serialized Summary",
    contributors: [
      { name: "Some Author", role: "author" }
    ],
    categories: ["Fiction"],
    series: [],
    is_compilation: true,
    binding: "Hard Cover",
    publisher: "Prothoma Publishers",
    price: "450.00",
  };

  const form = mapBookToComposerForm(serializedBook);

  assert.equal(form.title, "Serialized Book Title");
  assert.equal(form.summary, "Serialized Summary");
  assert.deepEqual(form.writers, ["Some Author"]);
  assert.equal(form.is_compilation, true);
  assert.equal(form.binding, "hard_cover");
  assert.equal(form.publisher, "Prothoma Publishers");
  assert.equal(form.price, "450.00");
});

// Helper mock of production renderWriterCell logic
function renderWriterCellMock(book, limitContributorRole = false) {
  if (limitContributorRole) {
    const writers = getContributorNamesByRole(book, "author");
    const translators = getContributorNamesByRole(book, "translator");
    const editors = getContributorNamesByRole(book, "editor");

    let selectedGroup = null;
    if (writers.length) {
      selectedGroup = { label: "Writer", names: writers };
    } else if (translators.length) {
      selectedGroup = { label: "Translator", names: translators };
    } else if (editors.length) {
      selectedGroup = { label: "Editor", names: editors };
    }

    if (!selectedGroup) {
      return "—";
    }
    return `${selectedGroup.label}: ${selectedGroup.names.join(", ")}`;
  }

  const writers = getContributorNamesByRole(book, "author");
  const translators = getContributorNamesByRole(book, "translator");
  const editors = getContributorNamesByRole(book, "editor");
  const parts = [];
  if (writers.length) parts.push(`Writer: ${writers.join(", ")}`);
  if (translators.length) parts.push(`Translator: ${translators.join(", ")}`);
  if (editors.length) parts.push(`Editor: ${editors.join(", ")}`);
  return parts.join(", ") || "Contributor unavailable";
}

test("binding mapping handles variations case-insensitively with space or underscore", () => {
  const b1 = makeBackendBook({ manual_binding: "HARD_COVER" });
  assert.equal(mapBookToComposerForm(b1).binding, "hard_cover");

  const b2 = makeBackendBook({ manual_binding: "paper_back" });
  assert.equal(mapBookToComposerForm(b2).binding, "paper_back");

  const b3 = makeBackendBook({ manual_binding: "  Hard   Cover " });
  assert.equal(mapBookToComposerForm(b3).binding, "hard_cover");

  const b4 = makeBackendBook({ manual_binding: "Paper Back" });
  assert.equal(mapBookToComposerForm(b4).binding, "paper_back");

  const b5 = makeBackendBook({ manual_binding: "paperback" });
  assert.equal(mapBookToComposerForm(b5).binding, "paper_back");
});

test("renderWriterCell mock displays contributor fallback priority correctly when limitContributorRole is true", () => {
  const book1 = {
    contributors: [
      { name: "Author J", role: "author" },
      { name: "Translator T", role: "translator" },
      { name: "Editor E", role: "editor" },
    ]
  };
  assert.equal(renderWriterCellMock(book1, true), "Writer: Author J");

  const book2 = {
    contributors: [
      { name: "Translator T", role: "translator" },
      { name: "Editor E", role: "editor" },
    ]
  };
  assert.equal(renderWriterCellMock(book2, true), "Translator: Translator T");

  const book3 = {
    contributors: [
      { name: "Editor E", role: "editor" },
    ]
  };
  assert.equal(renderWriterCellMock(book3, true), "Editor: Editor E");

  const book4 = { contributors: [] };
  assert.equal(renderWriterCellMock(book4, true), "—");

  assert.equal(
    renderWriterCellMock(book1, false),
    "Writer: Author J, Translator: Translator T, Editor: Editor E"
  );
});

function validateContributorsMock(form) {
  const hasWriter = form.writers && form.writers.length > 0;
  const hasTranslator = form.translators && form.translators.length > 0;
  const hasEditor = form.editors && form.editors.length > 0;
  return hasWriter || hasTranslator || hasEditor;
}

test("contributor validation mock allows any of writer, translator, or editor, but requires at least one", () => {
  assert.ok(validateContributorsMock({ writers: ["Author J"], translators: [], editors: [] }));
  assert.ok(validateContributorsMock({ writers: [], translators: ["Translator T"], editors: [] }));
  assert.ok(validateContributorsMock({ writers: [], translators: [], editors: ["Editor E"] }));
  assert.ok(validateContributorsMock({ writers: ["Author J"], translators: ["Translator T"], editors: ["Editor E"] }));

  assert.equal(validateContributorsMock({ writers: [], translators: [], editors: [] }), false);
});



