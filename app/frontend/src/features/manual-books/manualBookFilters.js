export const MANUAL_BOOKS_EXPORT_STORAGE_KEY = "manual-books-export";

export const emptyManualBookForm = {
  title: "",
  summary: "",
  writers: [],
  translators: [],
  editors: [],
  categories: [],
  series: [],
  is_compilation: false,
  binding: "hard_cover",
  publisher: "",
  price: ""
};

export const defaultManualBookFilters = {
  q: "",
  author: "",
  series: "",
  category: "",
  ownership: "",
  record_type: "manual",
  sort: "-created_at"
};

export const manualBookFilterFields = [
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
      { value: "catalog_code", label: "Code ascending" },
      { value: "-catalog_code", label: "Code descending" },
      { value: "title", label: "Title A-Z" },
      { value: "-title", label: "Title Z-A" }
    ]
  }
];

export const manualBookToolbarFields = manualBookFilterFields.filter(
  (field) => field.key !== "sort"
);

export const manualBookSortOptions =
  manualBookFilterFields.find((field) => field.key === "sort")?.options || [];
