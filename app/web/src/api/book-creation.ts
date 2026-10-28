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

export function uploadCreatedBookEpub(book: ManagedBookDetail, file: File) {
  const body = new FormData();
  body.set("expected_updated_at", book.updated_at); body.set("file", file);
  return apiMutation<ManagedBookDetail>(`manage/book-creations/${book.id}/epub/`, { method: "POST", body });
}

export function updateBookCover(book: ManagedBookDetail, file: File | null) {
  const path = `manage/books/${encodeURIComponent(book.slug)}/cover/`;
  if (file === null) return apiMutation<ManagedBookDetail>(path, { method: "DELETE", body: JSON.stringify({ expected_updated_at: book.updated_at }) });
  const body = new FormData();
  body.set("expected_updated_at", book.updated_at); body.set("image", file);
  return apiMutation<ManagedBookDetail>(path, { method: "POST", body });
}
