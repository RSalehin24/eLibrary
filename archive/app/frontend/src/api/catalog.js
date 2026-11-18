import { apiFetch } from "./client";

export function catalogFetch(path, options) {
  return apiFetch(path, options);
}

export function addBookToMyBooks(slug) {
  return catalogFetch(`/catalog/books/${slug}/my-books/`, { method: "POST" });
}

export function removeBookFromMyBooks(slug) {
  return catalogFetch(`/catalog/books/${slug}/my-books/`, { method: "DELETE" });
}

export async function sendBookToKindle(slug) {
  const payload = await apiFetch(`/access/books/${slug}/send-to-kindle/`, {
    method: "POST",
    body: {}
  });
  return payload;
}
