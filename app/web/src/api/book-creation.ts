import { apiMutation } from "./mutation";
import type { BookCreate, ManagedBookDetail } from "./types";

export const createCatalogBook = (values: BookCreate) => apiMutation<ManagedBookDetail>("manage/books/", {
  method: "POST", body: JSON.stringify(values),
});

export function uploadBookEpub(book: ManagedBookDetail, file: File) {
  const body = new FormData();
  body.set("expected_updated_at", book.updated_at); body.set("file", file);
  return apiMutation<ManagedBookDetail>(`manage/books/${encodeURIComponent(book.slug)}/epub/`, { method: "POST", body });
}
