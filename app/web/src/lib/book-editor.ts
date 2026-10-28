"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { runEditorialCommand, updateEditorial, type EditorialCommand } from "@/api/editorial";
import { updateBookCover, uploadBookEpub } from "@/api/book-creation";
import { regenerateBook, removeBook } from "@/api/book-lifecycle";
import type { BookEditorialUpdate, ManagedBookDetail } from "@/api/types";
import { useUnsavedChanges } from "./unsaved-changes";
import { useUpdateParticipant } from "./update-safety";

export function useBookEditor(initialBook: ManagedBookDetail) {
  const [book, setBook] = useState(initialBook);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState("");
  const router = useRouter();
  const client = useQueryClient();
  useUnsavedChanges(dirty);
  async function accept(updated: ManagedBookDetail) {
    setDirty(false); setBook(updated); setNotice("পরিবর্তন সংরক্ষিত হয়েছে।");
    await Promise.all([client.invalidateQueries({ queryKey: ["public", "books"] }), client.invalidateQueries({ queryKey: ["managed-books"] }), client.invalidateQueries({ queryKey: ["private", "book-controls"] }), client.invalidateQueries({ queryKey: ["private", "reader-access"] }), client.invalidateQueries({ queryKey: ["private", "book-detail-preview"] })]);
    if (updated.slug !== book.slug) router.replace(`/manage/books/${encodeURIComponent(updated.slug)}/`);
    router.refresh();
  }
  const save = useMutation({ mutationFn: (fields: Omit<BookEditorialUpdate, "expected_updated_at">) => updateEditorial(book, fields), onSuccess: accept });
  const command = useMutation({ mutationFn: (action: EditorialCommand) => runEditorialCommand(book, action), onSuccess: accept });
  const upload = useMutation({ mutationFn: (file: File) => uploadBookEpub(book, file), onSuccess: accept, retry: false, gcTime: 0 });
  const cover = useMutation({ mutationFn: (file: File | null) => updateBookCover(book, file), onSuccess: accept, retry: false, gcTime: 0 });
  const regenerate = useMutation({ mutationFn: (identifier: string) => regenerateBook(book, identifier), retry: false, onSuccess: async (result) => {
    await accept(result.book);
    await Promise.all([client.invalidateQueries({ queryKey: ["private", "sources"] }), client.invalidateQueries({ queryKey: ["private", "processing-assets"] })]);
  } });
  const remove = useMutation({ mutationFn: () => removeBook(book), retry: false, onSuccess: async () => {
    await Promise.all([client.invalidateQueries({ queryKey: ["managed-books"] }), client.invalidateQueries({ queryKey: ["private", "sources"] }), client.invalidateQueries({ queryKey: ["public", "books"] })]);
    router.push("/manage/books/"); router.refresh();
  } });
  const pending = save.isPending || command.isPending || upload.isPending || cover.isPending || regenerate.isPending || remove.isPending;
  useUpdateParticipant({ dirty: pending });
  return { book, dirty, notice, save, command, upload, cover, regenerate, remove, markDirty: () => { setDirty(true); setNotice(""); }, error: save.error ?? command.error, pending };
}

export type BookEditor = ReturnType<typeof useBookEditor>;
