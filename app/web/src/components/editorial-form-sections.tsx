"use client";

import { SiteDiv } from "@/components/site-language";

import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import type { EditorialCommand } from "@/api/editorial";
import type { ManagedBookDetail } from "@/api/types";
import { Icon } from "./icon";
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
  return <SiteDiv className="editorial-actions" aria-label="প্রকাশনা">
    <button className="button" disabled={pending || dirty || book.state === "published"} onClick={() => onCommand("publish")}><Icon name="upload" /><AdminText>{"প্রকাশ করুন"}</AdminText></button>
    <button className="button button-quiet" disabled={pending || dirty || book.state !== "published"} onClick={() => onCommand("withdraw")}><Icon name="logout" /><AdminText>{"প্রকাশনা প্রত্যাহার করুন"}</AdminText></button>
    {book.state === "published" && <Link className="text-link" href={`/books/${encodeURIComponent(book.slug)}/`}><Icon name="external" /><AdminText>{"প্রকাশিত পরিচিতি দেখুন →"}</AdminText></Link>}
  </SiteDiv>;
}
