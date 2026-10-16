import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { requireManagement } from "@/lib/workspace-session";
import { entityLabels, type EntityKind } from "@/lib/catalog-entity";

export const metadata = { title: "পরিচিতি পরিচালনা" };

export default async function ManagedEntitiesPage() {
  await requireManagement("books", "/manage/entities/");
  return <><h1><AdminText>{"পরিচিতি পরিচালনা"}</AdminText></h1>
    <p className="muted"><AdminText>{"লেখক, বিভাগ, সিরিজ ও নির্বাচিত সংগ্রহের পরিচিতি সম্পাদনা এবং পর্যালোচনা করুন।"}</AdminText></p>
    <ul className="management-list">{(Object.keys(entityLabels) as EntityKind[]).map((kind) => <li key={kind}>
      <h2><Link className="text-link" href={`/manage/entities/${kind}/`}><AdminText>{entityLabels[kind]}</AdminText></Link></h2>
    </li>)}</ul></>;
}
