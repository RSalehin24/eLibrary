"use client";

import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import type { ManagedEntity } from "@/api/types";
import type { EntityKind } from "@/lib/catalog-entity";
import { useEntityEditor } from "@/lib/entity-editor";
import { readEntityFields } from "@/lib/entity-form";
import { reloadManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";
import { EntityFields } from "./entity-fields";

export function EntityEditor({ kind, initialEntity }: { kind: EntityKind; initialEntity: ManagedEntity }) {
  const editor = useEntityEditor(kind, initialEntity);
  const { entity, blocked, dirty } = editor;
  return <section className="editorial-workspace">
    <div className="notice"><p><AdminText>{"পর্যালোচনা: "}</AdminText><AdminText>{entity.editorial_reviewed_at ? "অনুমোদিত" : "প্রয়োজন"}</AdminText></p>
      {kind === "collections" && <p><AdminText>{"অবস্থা: "}</AdminText>{entity.state === "published" ? "প্রকাশিত" : entity.state === "archived" ? "প্রত্যাহৃত" : "খসড়া"}<AdminText>{"। পরিচিতি ও বই নির্বাচন সংরক্ষণ করে পর্যালোচনা করুন, তারপর প্রকাশ করুন।"}</AdminText></p>}
      <p><AdminText>{"সম্পাদনার পরে আগের পর্যালোচনা বাতিল হয়।"}</AdminText></p></div>
    {dirty && <p role="status"><AdminText>{"আপনার কিছু পরিবর্তন এখনো সংরক্ষিত হয়নি।"}</AdminText></p>}
    {editor.notice && <p role="status">{editor.notice}</p>}
    <AccountFeedback error={editor.error} />
    {editor.error && <button className="button button-quiet" type="button" onClick={reloadManagedForm}><AdminText>{"নতুন তথ্য খুলুন"}</AdminText></button>}
    <form key={entity.updated_at} className="editorial-form" onChange={editor.markDirty} onSubmit={(event) => {
      event.preventDefault(); if (blocked) return;
      editor.command.reset(); editor.save.mutate(readEntityFields(event.currentTarget, kind));
    }}>
      <EntityFields kind={kind} entity={entity} disabled={blocked} errors={editor.errors} onChange={editor.markDirty} />
      <button className="button" disabled={blocked || !dirty}><AdminText>{"পরিবর্তন সংরক্ষণ করুন"}</AdminText></button>
    </form>
    <div className="editorial-actions" aria-label="পর্যালোচনা ও প্রকাশ">
      <button className="button button-quiet" disabled={blocked || dirty} onClick={() => { editor.save.reset(); editor.command.mutate("review"); }}><AdminText>{"পর্যালোচনা অনুমোদন করুন"}</AdminText></button>
      {kind === "collections" && <>
        <button className="button" disabled={blocked || dirty || !entity.editorial_reviewed_at || entity.state === "published"} onClick={() => { editor.save.reset(); editor.command.mutate("publish"); }}><AdminText>{"প্রকাশ করুন"}</AdminText></button>
        <button className="button button-quiet" disabled={blocked || dirty || entity.state !== "published"} onClick={() => { editor.save.reset(); editor.command.mutate("withdraw"); }}><AdminText>{"প্রকাশনা প্রত্যাহার করুন"}</AdminText></button>
        {entity.state === "published" && entity.editorial_reviewed_at && <Link className="text-link" href={`/collections/${encodeURIComponent(entity.slug)}/`}><AdminText>{"প্রকাশিত পরিচিতি দেখুন →"}</AdminText></Link>}
      </>}
    </div>
  </section>;
}
