"use client";

import { AdminText } from "@/components/admin-language";
import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { APIError } from "@/api/http";
import type { BookEditor } from "@/lib/book-editor";
import { reloadManagedForm } from "@/lib/managed-form";
import { useUnsavedChanges } from "@/lib/unsaved-changes";
import { AccountFeedback } from "./account-feedback";

export function BookEpubUpload({ editor }: { editor: BookEditor }) {
  const [file, setFile] = useState<File | null>(null);
  const element = useRef<HTMLFormElement>(null);
  const client = useQueryClient();
  const { book, upload, pending, dirty } = editor;
  const uncertain = !!upload.error && (!(upload.error instanceof APIError) || upload.error.status !== 400);
  const blocked = pending || dirty || uncertain;
  useUnsavedChanges(!!file);
  if (book.record_type !== "digital") return null;
  return <section className="account-section" id="book-upload"><h2><AdminText>{"EPUB আপলোড"}</AdminText></h2><p className="muted"><AdminText>{"সর্বোচ্চ ২৪ MiB। আপলোডের পরে পড়ার উপকরণ প্রস্তুত করুন এবং বইটি পর্যালোচনা করে প্রকাশ করুন।"}</AdminText></p>
    <form ref={element} onSubmit={(event) => {
      event.preventDefault(); if (!file || blocked) return;
      upload.mutate(file, { onSuccess: async () => { setFile(null); element.current?.reset(); await client.invalidateQueries({ queryKey: ["private", "processing-assets", book.slug] }); } });
    }}><div className="form-field"><label htmlFor="book-epub"><AdminText>{"বইয়ের EPUB ফাইল"}</AdminText></label><input id="book-epub" name="epub" type="file" accept=".epub,application/epub+zip" required disabled={blocked} onChange={(event) => { setFile(event.target.files?.[0] ?? null); upload.reset(); }} /></div>
      <button className="button" disabled={!file || blocked}><AdminText>{upload.isPending ? "আপলোড হচ্ছে…" : "EPUB আপলোড করুন"}</AdminText></button>
    </form>{dirty && <p className="notice"><AdminText>{"আপলোডের আগে বইয়ের অসম্পূর্ণ তথ্য সংরক্ষণ করুন।"}</AdminText></p>}
    <AccountFeedback error={upload.error} />
    {upload.error instanceof APIError && upload.error.fieldErrors.file && <p className="field-error" role="alert"><AdminText>{"সঠিক EPUB ফাইল দিন; আকার সর্বোচ্চ ২৪ MiB হতে পারে।"}</AdminText></p>}
    {upload.isSuccess && <p role="status"><AdminText>{"EPUB আপলোড হয়েছে। নিচের পড়ার উপকরণ থেকে প্রস্তুতির অনুরোধ করুন।"}</AdminText></p>}
    {uncertain && <button className="button button-quiet" onClick={reloadManagedForm}><AdminText>{"বর্তমান তথ্য খুলুন"}</AdminText></button>}
  </section>;
}
