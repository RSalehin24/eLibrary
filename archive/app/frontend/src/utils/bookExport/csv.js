import { escapeCsv, downloadBlob } from "./helpers";
import { bookExportRows } from "./rows";

export function exportBooksToCsv(books, filename) {
  const rows = bookExportRows(books);
  const header = [
    "Book ID",
    "Title",
    "Writer / Translator / Editor / Publisher",
    "Writers",
    "Translators",
    "Editors",
    "Publishers",
    "Categories",
    "Series",
    "Price",
    "Type",
    "State",
    "Review",
    "Created At",
  ];
  const lines = [
    header.join(","),
    ...rows.map((row) =>
      [
        row.catalogCode,
        row.title,
        row.contributors,
        row.authors,
        row.translators,
        row.editors,
        row.publishers,
        row.categories,
        row.series,
        row.price,
        row.type,
        row.state,
        row.review,
        row.createdAt,
      ]
        .map(escapeCsv)
        .join(","),
    ),
  ];
  downloadBlob(new Blob([`\ufeff${lines.join("\n")}`], { type: "text/csv;charset=utf-8" }), filename);
}
