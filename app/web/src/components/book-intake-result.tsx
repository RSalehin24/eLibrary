"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { APIError } from "@/api/http";
import { uploadCreatedBookEpub } from "@/api/book-creation";
import type { ManagedBookDetail } from "@/api/types";
import { useUnsavedChanges } from "@/lib/unsaved-changes";
import { AccountFeedback } from "./account-feedback";
import { AdminText } from "./admin-language";
import { BookActions } from "./book-actions";
import { FilePicker } from "./file-picker";

export function BookIntakeResult({ initialBook, canEdit }: { initialBook: ManagedBookDetail; canEdit: boolean }) {
  const [book, setBook] = useState(initialBook), [file, setFile] = useState<File | null>(null);
  const form = useRef<HTMLFormElement>(null);
  const upload = useMutation({ mutationFn: (selected: File) => uploadCreatedBookEpub(book, selected), retry: false,
    onSuccess: updated => { setBook(updated); setFile(null); form.current?.reset(); } });
  const uncertain = !!upload.error && (!(upload.error instanceof APIError) || upload.error.status !== 400);
  const blocked = upload.isPending || uncertain;
  useUnsavedChanges(!!file || upload.isPending);
  return <section className="admin-result-panel"><h2>{book.title}</h2>
    {book.state === "draft" && <><p><AdminText>EPUB প্রস্তুত হলে বইটি স্বয়ংক্রিয়ভাবে প্রকাশিত হবে।</AdminText></p>
      <form ref={form} onSubmit={event => { event.preventDefault(); if (file && !blocked) upload.mutate(file); }}>
        <div className="form-field"><label htmlFor="intake-epub"><AdminText>বইয়ের EPUB ফাইল</AdminText></label><FilePicker id="intake-epub" name="epub" type="file" accept=".epub,application/epub+zip" required disabled={blocked} onChange={event => { setFile(event.target.files?.[0] ?? null); upload.reset(); }} /></div>
        <button className="button" disabled={!file || blocked}><AdminText>{upload.isPending ? "আপলোড হচ্ছে…" : "EPUB আপলোড করুন"}</AdminText></button>
      </form></>}
    <AccountFeedback error={upload.error} />
    {uncertain && <Link className="button button-quiet" href={`/manage/book-creations/${book.id}/`}><AdminText>এই অনুরোধের ফল দেখুন →</AdminText></Link>}
    {book.state === "published" && <><p role="status"><AdminText>EPUB ও HTML প্রস্তুত হয়েছে। বইটি এখন পড়া যাবে।</AdminText></p><BookActions slug={book.slug} />
      <Link className="button button-quiet" href={`/books/${encodeURIComponent(book.slug)}/`}><AdminText>প্রকাশিত পরিচিতি দেখুন →</AdminText></Link></>}
    {canEdit && book.state !== "published" && <Link className="button button-quiet" href={`/manage/books/${encodeURIComponent(book.slug)}/`}><AdminText>বইয়ের তথ্য সম্পাদনা করুন</AdminText></Link>}
  </section>;
}
