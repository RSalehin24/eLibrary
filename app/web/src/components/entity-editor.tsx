"use client";

import { SiteDiv } from "@/components/site-language";

import { catalogStateLabel } from "@/lib/catalog-state";
import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import type { ManagedEntity } from "@/api/types";
import type { EntityKind } from "@/lib/catalog-entity";
import { useEntityEditor } from "@/lib/entity-editor";
import { readEntityFields } from "@/lib/entity-form";
import { reloadManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";
import { Icon } from "./icon";
import { EntityFields } from "./entity-fields";

export function EntityEditor({ kind, initialEntity }: { kind: EntityKind; initialEntity: ManagedEntity }) {
  const editor = useEntityEditor(kind, initialEntity);
  const { entity, blocked, dirty } = editor;
  return <section className="editorial-workspace">
    {kind === "collections" && <p className="notice"><AdminText>{"অবস্থা: "}</AdminText><AdminText>{catalogStateLabel(entity.state)}</AdminText></p>}
    {dirty && <p role="status"><AdminText>{"আপনার কিছু পরিবর্তন এখনো সংরক্ষিত হয়নি।"}</AdminText></p>}
    {editor.notice && <p role="status">{editor.notice}</p>}
    <AccountFeedback error={editor.error} />
    {editor.error && <button className="button button-quiet" type="button" onClick={reloadManagedForm}><AdminText>{"নতুন তথ্য খুলুন"}</AdminText></button>}
    <form key={entity.updated_at} className="editorial-form" onChange={editor.markDirty} onSubmit={(event) => {
      event.preventDefault(); if (blocked) return;
      editor.command.reset(); editor.save.mutate(readEntityFields(event.currentTarget, kind));
    }}>
      <EntityFields kind={kind} entity={entity} disabled={blocked} errors={editor.errors} onChange={editor.markDirty} />
      <button className="button" disabled={blocked || !dirty}><Icon name="save" /><AdminText>{"পরিবর্তন সংরক্ষণ করুন"}</AdminText></button>
    </form>
    <SiteDiv className="editorial-actions" aria-label="প্রকাশনা">
      {kind === "collections" && <>
        <button className="button" disabled={blocked || dirty || entity.state === "published"} onClick={() => { editor.save.reset(); editor.command.mutate("publish"); }}><Icon name="upload" /><AdminText>{"প্রকাশ করুন"}</AdminText></button>
        <button className="button button-quiet" disabled={blocked || dirty || entity.state !== "published"} onClick={() => { editor.save.reset(); editor.command.mutate("withdraw"); }}><Icon name="logout" /><AdminText>{"প্রকাশনা প্রত্যাহার করুন"}</AdminText></button>
        {entity.state === "published" && <Link className="text-link" href={`/collections/${encodeURIComponent(entity.slug)}/`}><AdminText>{"প্রকাশিত পরিচিতি দেখুন →"}</AdminText></Link>}
      </>}
    </SiteDiv>
  </section>;
}
