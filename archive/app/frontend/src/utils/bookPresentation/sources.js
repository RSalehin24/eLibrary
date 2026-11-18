import { getStatusMeta } from "./meta";

export function getBookCardCaption(book) {
  const sourceTitle = book.primary_source?.source_title;
  const sourcePath = book.primary_source?.display_path;
  return sourceTitle || sourcePath || "Source record will appear here after review";
}

export function getSourceLabel(source) {
  if (!source) {
    return "";
  }
  return source.source_title || source.display_path || source.display_url || source.url || "";
}

export function getSourceHostLabel(source) {
  return source?.site ? source.site.replace(/^www\./, "") : "";
}

export function getBookReadinessSummary(book) {
  const lifecycle = getStatusMeta(book.state);
  const review = getStatusMeta(book.review_state);
  return [lifecycle.label, review.label].filter(Boolean).join(" · ");
}

