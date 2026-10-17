"use client";

import { useQuery } from "@tanstack/react-query";
import { readerAccess } from "@/api/reading";
import { BookCover } from "./book-cover";

export function ReaderBookCover({ slug, title, author }: { slug: string; title: string; author?: string }) {
  const access = useQuery({ queryKey: ["private", "reader-access", slug], queryFn: ({ signal }) => readerAccess(slug, signal), refetchInterval: 5000, refetchIntervalInBackground: false });
  return <BookCover key={access.data?.cover_url ?? "placeholder"} title={title} author={author} coverUrl={access.data?.cover_url} />;
}
