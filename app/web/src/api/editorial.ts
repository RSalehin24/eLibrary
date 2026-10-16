import { apiMutation } from "./mutation";
import type { BookEditorialUpdate, ManagedBookDetail } from "./types";

export type EditorialCommand = "review" | "publish" | "withdraw";

export async function updateEditorial(book: ManagedBookDetail, fields: Omit<BookEditorialUpdate, "expected_updated_at">) {
  return editorialRequest(`manage/books/${encodeURIComponent(book.slug)}/`, "PATCH", {
    ...fields, expected_updated_at: book.updated_at,
  });
}

export async function runEditorialCommand(book: ManagedBookDetail, command: EditorialCommand) {
  return editorialRequest(`manage/books/${encodeURIComponent(book.slug)}/${command}/`, "POST", {
    expected_updated_at: book.updated_at,
  });
}

async function editorialRequest(path: string, method: string, fields: BookEditorialUpdate) {
  return apiMutation<ManagedBookDetail>(path, { method, body: JSON.stringify(fields) });
}
