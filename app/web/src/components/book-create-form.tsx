"use client";

import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createCatalogBook } from "@/api/book-creation";
import type { BookCreate } from "@/api/types";
import { readBookFormat } from "@/lib/book-format";
import { useManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";
import { BookFormatFields } from "./book-format-fields";
import { EditorialField } from "./editorial-field";

const emptyFormat = { edition: "", manual_language: "bn", manual_publisher: "", manual_price: null, manual_binding: "" as const, manual_is_compilation: false };

export function BookCreateForm({ initialRecordType = "digital" }: { initialRecordType?: BookCreate["record_type"] }) {
  const [operation, setOperation] = useState<string | null>(null);
  const client = useQueryClient();
  const form = useManagedForm(createCatalogBook, async () => { await client.invalidateQueries({ queryKey: ["managed-books"] }); });
  if (form.saving.isSuccess) return <section className="notice"><h2><AdminText>{"বইয়ের নথি তৈরি হয়েছে"}</AdminText></h2><p><AdminText>{"তথ্য সম্পাদনা ও পর্যালোচনা শেষ করে প্রকাশ করতে পারবেন।"}</AdminText></p>
    <Link className="button" href={`/manage/books/${encodeURIComponent(form.saving.data.slug)}/`}><AdminText>{"বইয়ের তথ্য সম্পাদনা করুন"}</AdminText></Link>
    {form.saving.data.record_type === "digital" && <Link className="text-link" href={`/manage/books/${encodeURIComponent(form.saving.data.slug)}/#book-upload`}><AdminText>{"EPUB আপলোড করুন →"}</AdminText></Link>}</section>;
  return <form className="editorial-form" onChange={form.markDirty} onSubmit={(event) => {
    event.preventDefault(); if (form.blocked) return;
    const fields = new FormData(event.currentTarget), identifier = operation ?? crypto.randomUUID(); setOperation(identifier);
    form.saving.mutate({ ...readBookFormat(fields), operation_id: identifier, title: String(fields.get("title")), summary: String(fields.get("summary")), record_type: String(fields.get("record_type")) as BookCreate["record_type"] });
  }}><fieldset disabled={form.blocked}><legend><AdminText>{"বইয়ের পরিচিতি"}</AdminText></legend>
    <EditorialField name="title" label="বইয়ের নাম" value="" maxLength={255} errors={form.errors.title} />
    <div className="form-field"><label htmlFor="record_type"><AdminText>{"বইয়ের ধরন"}</AdminText></label><select id="record_type" name="record_type" defaultValue={initialRecordType}><option value="digital"><AdminText>{"ডিজিটাল বই"}</AdminText></option><option value="manual"><AdminText>{"কাগজের বই"}</AdminText></option></select></div>
    <EditorialField name="summary" label="সংক্ষিপ্ত পরিচিতি" value="" maxLength={20000} errors={form.errors.summary} multiline />
  </fieldset><BookFormatFields book={emptyFormat} pending={form.blocked} errors={form.errors} />
    <AccountFeedback error={form.saving.error} /><button className="button" disabled={form.blocked}><AdminText>{"বইয়ের নথি তৈরি করুন"}</AdminText></button>
    {form.saving.error && operation && <Link className="text-link" href={`/manage/book-creations/${operation}/`}><AdminText>{"এই অনুরোধের ফল দেখুন →"}</AdminText></Link>}
    <Link className="text-link" href="/manage/books/"><AdminText>{"← বইয়ের তালিকায় ফিরুন"}</AdminText></Link></form>;
}
