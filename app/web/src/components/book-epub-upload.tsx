"use client";

import { FilePicker } from "./file-picker";


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
  const sourceMismatch = upload.error instanceof APIError && upload.error.fieldErrors.file?.some((message) => message.startsWith("The EPUB reading text does not match"));
  const sourceProofMissing = upload.error instanceof APIError && /Regenerate the website book|retained source evidence/.test(upload.error.detail);
  return <section className="account-section" id="book-upload"><h2><AdminText>{"EPUB আপলোড"}</AdminText></h2><p className="muted"><AdminText>{"সর্বোচ্চ ২৪ MiB। বই পড়ার ফাইল স্বয়ংক্রিয়ভাবে পরীক্ষা ও প্রস্তুত হবে। সব পরীক্ষা সফল হলে নতুন ফাইল চালু হবে; ততক্ষণ প্রকাশিত বইয়ের আগের ফাইল চালু থাকবে।"}</AdminText></p>
    <form ref={element} onSubmit={(event) => {
      event.preventDefault(); if (!file || blocked) return;
      upload.mutate(file, { onSuccess: async () => { setFile(null); element.current?.reset(); await client.invalidateQueries({ queryKey: ["private", "processing-assets", book.slug] }); } });
    }}><div className="form-field"><label htmlFor="book-epub"><AdminText>{"বইয়ের EPUB ফাইল"}</AdminText></label><FilePicker id="book-epub" name="epub" type="file" accept=".epub,application/epub+zip" required disabled={blocked} onChange={(event) => { setFile(event.target.files?.[0] ?? null); upload.reset(); }} /></div>
      <button className="button" disabled={!file || blocked}><AdminText>{upload.isPending ? "আপলোড হচ্ছে…" : "EPUB আপলোড করুন"}</AdminText></button>
    </form>{dirty && <p className="notice"><AdminText>{"আপলোডের আগে বইয়ের অসম্পূর্ণ তথ্য সংরক্ষণ করুন।"}</AdminText></p>}
    {!sourceMismatch && !sourceProofMissing && <AccountFeedback error={upload.error} />}
    {sourceProofMissing && <p className="field-error" role="alert"><AdminText>{"ওয়েবসাইটের বইটি আবার তৈরি করুন। লেখার স্বয়ংক্রিয় যাচাই শেষ হলে একই লেখার EPUB আপলোড করতে পারবেন।"}</AdminText></p>}
    {upload.error instanceof APIError && upload.error.fieldErrors.file && <p className="field-error" role="alert"><AdminText>{sourceMismatch ? "EPUB-এ ওয়েবসাইটের সব অধ্যায়ের লেখা মেলেনি। বইটি আবার তৈরি করুন অথবা একই লেখার সম্পূর্ণ EPUB দিন। আগের ফাইল বদলায়নি।" : "সঠিক EPUB ফাইল দিন; আকার সর্বোচ্চ ২৪ MiB হতে পারে।"}</AdminText></p>}
    {upload.isSuccess && <p role="status"><AdminText>{"EPUB পরীক্ষা করে পড়ার জন্য প্রস্তুত করা হয়েছে। প্রকাশিত বইয়ে নতুন ফাইল চালু হয়েছে। নতুন বই হলে প্রকাশ করুন বাটন ব্যবহার করুন।"}</AdminText></p>}
    {uncertain && <button className="button button-quiet" onClick={reloadManagedForm}><AdminText>{"বর্তমান তথ্য খুলুন"}</AdminText></button>}
  </section>;
}
