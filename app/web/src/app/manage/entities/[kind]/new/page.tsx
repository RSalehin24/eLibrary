import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { EntityCreateForm } from "@/components/entity-create-form";
import { entityLabels } from "@/lib/catalog-entity";
import { managedEntityKind } from "@/lib/managed-entity";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "পরিচিতি তৈরি" }); }

export default async function CreateEntityPage({ params }: { params: Promise<{ kind: string }> }) {
  const kind = managedEntityKind((await params).kind);
  const session = await requireManagement("books", `/manage/entities/${kind}/new/`);
  if (!session.workspaces.can_create_books) notFound();
  return <><Link className="text-link" href={`/manage/entities/${kind}/`}><AdminText>{"← তালিকায় ফিরুন"}</AdminText></Link><h1><AdminText>{entityLabels[kind]}</AdminText><AdminText>{": পরিচিতি তৈরি"}</AdminText></h1>
    <EntityCreateForm kind={kind} /></>;
}
