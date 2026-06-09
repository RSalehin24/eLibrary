export const LIBRARY_EXPORT_STORAGE_KEY = "catalog-books-export";

export const defaultLibraryFilters = {
  q: "",
  author: "",
  series: "",
  category: "",
  contributor: "",
  contributor_role: "",
  ownership: "",
  record_type: "digital",
  sort: "-created_at"
};

export const libraryFilterFields = [
  { key: "author", label: "Contributor" },
  { key: "series", label: "Series" },
  { key: "category", label: "Category" },
  {
    key: "ownership",
    label: "Ownership",
    type: "select",
    options: [
      { value: "", label: "All books" },
      { value: "mine", label: "My books" }
    ]
  },
  {
    key: "record_type",
    label: "Type",
    type: "select",
    options: [
      { value: "digital", label: "Digital" },
      { value: "manual", label: "Manual" },
      { value: "all", label: "All types" }
    ]
  },
  {
    key: "sort",
    label: "Sort",
    type: "select",
    options: [
      { value: "-created_at", label: "Newest first" },
      { value: "created_at", label: "Oldest first" },
      { value: "-requested_at", label: "Newest request first" },
      { value: "requested_at", label: "Oldest request first" },
      { value: "catalog_code", label: "Code ascending" },
      { value: "-catalog_code", label: "Code descending" },
      { value: "title", label: "Title A-Z" },
      { value: "-title", label: "Title Z-A" }
    ]
  }
];

export const libraryToolbarFields = libraryFilterFields.filter(
  (field) => field.key !== "sort"
);

export const librarySortOptions =
  libraryFilterFields.find((field) => field.key === "sort")?.options || [];
