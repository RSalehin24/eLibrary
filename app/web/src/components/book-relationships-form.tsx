"use client";

import { AdminText } from "@/components/admin-language";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { updateBookRelationships } from "@/api/book-relationships";
import type { BookRelationships, BookRelationshipsUpdate } from "@/api/types";
import { reloadManagedForm, useManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";
import { BookContributorSelector } from "./book-contributor-selector";
import { BookEditionSelector } from "./book-edition-selector";
import { CatalogReferenceSelector } from "./catalog-reference-selector";
import { EditorialField } from "./editorial-field";

export function BookRelationshipsForm({ slug, initialRelationships }: { slug: string; initialRelationships: BookRelationships }) {
  const [relationships, setRelationships] = useState(initialRelationships);
  const router = useRouter();
  const form = useManagedForm((fields: BookRelationshipsUpdate) => updateBookRelationships(slug, fields), async (updated) => { setRelationships(updated); router.refresh(); });
  return <section className="editorial-workspace">
    <p className="muted"><AdminText>{"এই সম্পর্কগুলো বইয়ের অনুমতি নির্ধারণেও ব্যবহৃত হয়। সংরক্ষণের পরে পরিবর্তন কার্যকর হবে।"}</AdminText></p>
    {form.saving.isSuccess && !form.dirty && <p role="status"><AdminText>{"বইয়ের সম্পর্ক সংরক্ষিত হয়েছে।"}</AdminText></p>}
    <form key={relationships.updated_at} className="editorial-form" onChange={form.markDirty} onSubmit={(event) => {
      event.preventDefault(); if (form.blocked) return;
      const fields = new FormData(event.currentTarget);
      const contributors = JSON.parse(String(fields.get("contributors"))) as BookRelationshipsUpdate["contributors"];
      form.saving.mutate({ expected_updated_at: relationships.updated_at, edit_note: String(fields.get("edit_note") ?? ""), contributors, category_ids: fields.getAll("category_ids").map(String), series_ids: fields.getAll("series_ids").map(String),
        ...(fields.has("edition_of") ? { edition_of: String(fields.get("edition_of")) || null } : {}) });
    }}>
      <BookContributorSelector initialSelection={relationships.contributors} disabled={form.blocked} errors={form.errors.contributors} onChange={form.markDirty} />
      <CatalogReferenceSelector kind="categories" label="বিভাগ" name="category_ids" initialSelection={relationships.categories} disabled={form.blocked} errors={form.errors.category_ids} onChange={form.markDirty} />
      <CatalogReferenceSelector kind="series" label="সিরিজ" name="series_ids" initialSelection={relationships.series} disabled={form.blocked} errors={form.errors.series_ids} onChange={form.markDirty} />
      <BookEditionSelector relationships={relationships} disabled={form.blocked} errors={form.errors.edition_of} onChange={form.markDirty} />
      <fieldset disabled={form.blocked}><EditorialField name="edit_note" label="পরিবর্তনের কারণ (ঐচ্ছিক)" value="" errors={form.errors.edit_note} maxLength={2000} multiline /></fieldset>
      <AccountFeedback error={form.saving.error} />
      {form.saving.error && <button className="button button-quiet" type="button" onClick={reloadManagedForm}><AdminText>{"নতুন তথ্য খুলুন"}</AdminText></button>}
      <button className="button" disabled={form.blocked || !form.dirty}><AdminText>{"বইয়ের সম্পর্ক সংরক্ষণ করুন"}</AdminText></button>
    </form>
  </section>;
}
