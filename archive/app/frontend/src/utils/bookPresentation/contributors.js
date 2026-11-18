import { formatRole } from "./formatters";

const CONTRIBUTOR_ROLE_ORDER = [
  "author",
  "translator",
  "editor",
  "illustrator",
  "cover_artist",
  "publisher",
  "other",
];
const PRIMARY_CONTRIBUTOR_ROLE_ORDER = ["author", "translator", "editor"];
const CONTRIBUTOR_ROLE_LABELS = {
  author: "",
  translator: "Translator",
  editor: "Editor",
  illustrator: "Illustration",
  cover_artist: "Cover",
  publisher: "Publisher",
  other: "Contributor",
};

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
      if (!entry?.name) {
        return;
      }
      const role = canonicalContributorRole(entry.role);
      const normalizedName = normalizeContributorName(entry.name);
      const contributorKey = `${normalizedName}|${role}`;
      if (!normalizedName || exactSeen.has(contributorKey)) {
        return;
      }
      exactSeen.add(contributorKey);
      if (role !== "author") {
        nonAuthorNames.add(normalizedName);
      }
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

export function getContributorRoleLabel(value) {
  return CONTRIBUTOR_ROLE_LABELS[value] || formatRole(value);
}

export function getContributorNamesByRole(book, role) {
  return getNormalizedContributorEntries(book)
    .filter((entry) => entry.role === role)
    .map((entry) => entry.name)
    .filter(Boolean);
}

export function getAuthorNames(book) {
  return getContributorNamesByRole(book, "author");
}

export function getWriterColumnGroups(book) {
  const roleConfigs = [
    { role: "author", label: "", queryKey: "author" },
    { role: "translator", label: "Translator", queryKey: "contributor" },
    { role: "editor", label: "Editor", queryKey: "contributor" },
  ];
  return roleConfigs
    .map((config) => ({ ...config, names: getContributorNamesByRole(book, config.role) }))
    .filter((config) => config.names.length)
    .map(({ label, names, queryKey }) => ({ label, names, queryKey }));
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
      if (!names.length) {
        return "";
      }
      return label ? `${label}: ${names.join(", ")}` : names.join(", ");
    })
    .filter(Boolean);
  return parts.join(" · ") || "Contributor unavailable";
}

export function getContributorGroups(book) {
  const grouped = new Map();
  getNormalizedContributorEntries(book).forEach((entry) => {
    const role = canonicalContributorRole(entry.role);
    const names = grouped.get(role) || [];
    if (!names.includes(entry.name)) {
      grouped.set(role, [...names, entry.name]);
    }
  });
  return CONTRIBUTOR_ROLE_ORDER.filter((role) => grouped.has(role)).map((role) => ({
    role,
    label: getContributorRoleLabel(role),
    names: grouped.get(role),
  }));
}

export function getPrimaryContributorGroup(book) {
  const groups = getContributorGroups(book);
  return groups.find((group) => PRIMARY_CONTRIBUTOR_ROLE_ORDER.includes(group.role)) || groups[0] || null;
}

export function getPrimaryContributorName(book) {
  return getPrimaryContributorGroup(book)?.names?.[0] || "";
}

export function getContributorLine(book) {
  return getContributorGroups(book)
    .map((group) => (group.label ? `${group.label}: ${group.names.join(", ")}` : group.names.join(", ")))
    .join(" · ");
}
