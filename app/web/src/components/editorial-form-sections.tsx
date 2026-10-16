"use client";

import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import type { EditorialCommand } from "@/api/editorial";
import type { ManagedBookDetail } from "@/api/types";
import { EditorialField } from "./editorial-field";
import { EditorialTextFields } from "./editorial-metadata-fields";

type FieldGroupProps = { book: ManagedBookDetail; errors: Record<string, string[]>; pending: boolean };

export function BookMetadataFields({ book, errors, pending }: FieldGroupProps) {
  return <fieldset disabled={pending}>
    <legend><AdminText>{"বইয়ের তথ্য"}</AdminText></legend>
    <EditorialField name="title" label="বইয়ের নাম" value={book.title} errors={errors.title} maxLength={255} />
    <EditorialField name="summary" label="সংক্ষিপ্ত পরিচিতি" value={book.summary} errors={errors.summary} multiline maxLength={20000} />
    <EditorialTextFields values={book} errors={errors} />
  </fieldset>;
}

type ActionProps = { book: ManagedBookDetail; pending: boolean; dirty: boolean; onCommand: (action: EditorialCommand) => void };

export function EditorialActions({ book, pending, dirty, onCommand }: ActionProps) {
  return <div className="editorial-actions" aria-label="পর্যালোচনা ও প্রকাশ">
    <button className="button button-quiet" disabled={pending || dirty} onClick={() => onCommand("review")}><AdminText>{"পর্যালোচনা অনুমোদন করুন"}</AdminText></button>
    <button className="button" disabled={pending || dirty || !book.editorial_reviewed_at || book.state === "published"} onClick={() => onCommand("publish")}><AdminText>{"প্রকাশ করুন"}</AdminText></button>
    <button className="button button-quiet" disabled={pending || dirty || book.state !== "published"} onClick={() => onCommand("withdraw")}><AdminText>{"প্রকাশনা প্রত্যাহার করুন"}</AdminText></button>
    {book.state === "published" && book.review_state === "approved" && <Link className="text-link" href={`/books/${encodeURIComponent(book.slug)}/`}><AdminText>{"প্রকাশিত পরিচিতি দেখুন →"}</AdminText></Link>}
  </div>;
}
