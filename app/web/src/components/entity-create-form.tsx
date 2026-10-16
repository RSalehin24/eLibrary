"use client";

import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createManagedEntity } from "@/api/entities";
import { useManagedForm } from "@/lib/managed-form";
import type { EntityKind } from "@/lib/catalog-entity";
import { emptyEditorial } from "@/lib/editorial-fields";
import { readEntityFields } from "@/lib/entity-form";
import type { EntityCreate } from "@/api/types";
import { AccountFeedback } from "./account-feedback";
import { EntityFields } from "./entity-fields";

export function EntityCreateForm({ kind }: { kind: EntityKind }) {
  const [operation, setOperation] = useState<string | null>(null);
  const client = useQueryClient();
  const form = useManagedForm((values: EntityCreate) => createManagedEntity(kind, values), async () => { await client.invalidateQueries({ queryKey: ["private", "catalog-references"] }); });
  if (form.saving.isSuccess) return <section className="notice"><h2><AdminText>{"পরিচিতি তৈরি হয়েছে"}</AdminText></h2>
    <Link className="button" href={`/manage/entities/${kind}/${form.saving.data.id}/`}><AdminText>{"তথ্য সম্পাদনা ও পর্যালোচনা করুন"}</AdminText></Link></section>;
  return <form className="editorial-form" onChange={form.markDirty} onSubmit={(event) => {
    event.preventDefault(); if (form.blocked) return;
    const identifier = operation ?? crypto.randomUUID(); setOperation(identifier);
    form.saving.mutate({ ...readEntityFields(event.currentTarget, kind), operation_id: identifier });
  }}>
    <EntityFields kind={kind} entity={{ ...emptyEditorial, name: "", selected_books: [] }} disabled={form.blocked} errors={form.errors} onChange={form.markDirty} />
    <AccountFeedback error={form.saving.error} />
    <button className="button" disabled={form.blocked}><AdminText>{"পরিচিতি তৈরি করুন"}</AdminText></button>
    {form.saving.error && operation && <Link className="text-link" href={`/manage/entities/${kind}/${operation}/`}><AdminText>{"এই অনুরোধের বর্তমান পরিচিতি দেখুন →"}</AdminText></Link>}
  </form>;
}
