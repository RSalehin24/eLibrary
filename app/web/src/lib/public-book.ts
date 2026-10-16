import { cache } from "react";
import { notFound, permanentRedirect } from "next/navigation";
import { APIError } from "@/api/http";
import { publicRequest } from "@/api/server";
import type { PublicBookDetail } from "@/api/types";

export const getPublicBook = cache(async (slug: string) => {
  let book: PublicBookDetail;
  try {
    book = await publicRequest<PublicBookDetail>(`catalog/books/${encodeURIComponent(slug)}/`);
  } catch (error) {
    if (error instanceof APIError && error.status === 404) notFound();
    throw error;
  }
  if (book.slug !== slug) permanentRedirect(`/books/${encodeURIComponent(book.slug)}/`);
  return book;
});
