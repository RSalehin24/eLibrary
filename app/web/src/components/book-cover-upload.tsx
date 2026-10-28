"use client";

import { useRef, useState } from "react";
import { APIError } from "@/api/http";
import type { BookEditor } from "@/lib/book-editor";
import { useUnsavedChanges } from "@/lib/unsaved-changes";
import { reloadManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";
import { AdminText } from "./admin-language";
import { FilePicker } from "./file-picker";
import { SiteFieldErrors } from "./site-field-errors";

export function BookCoverUpload({ editor }: { editor: BookEditor }) {
  const { book, cover, pending, dirty } = editor;
  const [file, setFile] = useState<File | null>(null), form = useRef<HTMLFormElement>(null);
  const uncertain = !!cover.error && (!(cover.error instanceof APIError) || cover.error.status !== 400);
  const blocked = pending || dirty || uncertain;
  const imageErrors = cover.error instanceof APIError ? cover.error.fieldErrors.image : undefined;
  useUnsavedChanges(!!file);
  return <section className="account-section" id="book-cover"><h2><AdminText>প্রচ্ছদ</AdminText></h2>
    <p className="muted"><AdminText>PNG, JPEG বা WebP ছবি দিন। সর্বোচ্চ ৫ MiB এবং ২০৪৮×২০৪৮ পিক্সেল।</AdminText></p>
    <form ref={form} onSubmit={event => { event.preventDefault(); if (file && !blocked) cover.mutate(file, { onSuccess: () => { setFile(null); form.current?.reset(); } }); }}>
      <div className="form-field"><label htmlFor="book-cover-image"><AdminText>নতুন প্রচ্ছদ</AdminText></label><FilePicker id="book-cover-image" name="image" type="file" accept="image/png,image/jpeg,image/webp" disabled={blocked} aria-invalid={!!imageErrors} aria-describedby={imageErrors ? "book-cover-error" : undefined} onChange={event => { setFile(event.target.files?.[0] ?? null); cover.reset(); }} /></div>
      {imageErrors && <p className="field-error" id="book-cover-error"><SiteFieldErrors errors={imageErrors} /></p>}
      <button className="button" disabled={!file || blocked}><AdminText>{cover.isPending ? "সংরক্ষণ হচ্ছে…" : "প্রচ্ছদ সংরক্ষণ করুন"}</AdminText></button>
      <button className="button button-quiet" type="button" disabled={!book.cover_url || blocked} onClick={() => cover.mutate(null)}><AdminText>প্রচ্ছদ সরান</AdminText></button>
    </form>
    <AccountFeedback error={cover.error} />
    {uncertain && <button className="button button-quiet" onClick={reloadManagedForm}><AdminText>বর্তমান তথ্য খুলুন</AdminText></button>}
  </section>;
}
