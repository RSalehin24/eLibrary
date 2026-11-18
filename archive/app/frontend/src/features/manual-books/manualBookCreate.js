import { catalogFetch } from "../../api/catalog";

export async function createManualBook(form) {
  return catalogFetch("/catalog/manual-books/", {
    method: "POST",
    body: {
      ...form,
      price: form.price === "" ? null : form.price
    }
  });
}
