import assert from "node:assert/strict";
import test from "node:test";
import { normalizeContributorName, canonicalContributorRole, getNormalizedContributorEntries, getContributorNamesByRole, mapBookToComposerForm, mapComposerFormToPayload, makeBackendBook, renderWriterCellMock, validateContributorsMock } from '../support/physical-book-fixtures.js';


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


test("contributor validation mock allows any of writer, translator, or editor, but requires at least one", () => {
  assert.ok(validateContributorsMock({ writers: ["Author J"], translators: [], editors: [] }));
  assert.ok(validateContributorsMock({ writers: [], translators: ["Translator T"], editors: [] }));
  assert.ok(validateContributorsMock({ writers: [], translators: [], editors: ["Editor E"] }));
  assert.ok(validateContributorsMock({ writers: ["Author J"], translators: ["Translator T"], editors: ["Editor E"] }));

  assert.equal(validateContributorsMock({ writers: [], translators: [], editors: [] }), false);
});
