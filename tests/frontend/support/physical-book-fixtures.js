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

export function mapBookToComposerForm(book) {
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

export function mapComposerFormToPayload(form) {
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

export function makeBackendBook(overrides = {}) {
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

export function renderWriterCellMock(book, limitContributorRole = false) {
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

export function validateContributorsMock(form) {
  const hasWriter = form.writers && form.writers.length > 0;
  const hasTranslator = form.translators && form.translators.length > 0;
  const hasEditor = form.editors && form.editors.length > 0;
  return hasWriter || hasTranslator || hasEditor;
}
