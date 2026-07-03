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
  price: "",
  language: "bn",
};

export const defaultManualBookFilters = {
  q: "",
  writer: "",
  translator: "",
  editor: "",
  category: "",
  publisher: "",
  binding: "",
  ownership: "",
  record_type: "manual",
  sort: "-created_at"
};

export const manualBookFilterFields = [
  { key: "writer", label: "Writer" },
  { key: "translator", label: "Translator" },
  { key: "editor", label: "Editor" },
  { key: "category", label: "Category" },
  { key: "publisher", label: "Publisher" },
  {
    key: "binding",
    label: "Binding",
    type: "select",
    options: [
      { value: "", label: "Any" },
      { value: "hard_cover", label: "Hardcover" },
      { value: "paper_back", label: "Paperback" }
    ]
  },
  {
    key: "sort",
    label: "Sort",
    type: "select",
    options: [
      { value: "-created_at", label: "Newest first" },
      { value: "created_at", label: "Oldest first" },
      { value: "title", label: "Title A-Z" },
      { value: "-title", label: "Title Z-A" },
      { value: "manual_publisher", label: "Publisher A-Z" },
      { value: "-manual_publisher", label: "Publisher Z-A" }
    ]
  }
];

export const manualBookToolbarFields = manualBookFilterFields.filter(
  (field) => field.key !== "sort"
);

export const manualBookSortOptions =
  manualBookFilterFields.find((field) => field.key === "sort")?.options || [];
