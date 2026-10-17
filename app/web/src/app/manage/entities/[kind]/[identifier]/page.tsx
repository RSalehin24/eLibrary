import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { ManagedEntity } from "@/api/types";
import { entityFilters } from "@/lib/catalog-entity";
import { Icon } from "@/components/icon";
import { EntityNavigation } from "@/components/entity-navigation";
import { EntityEditor } from "@/components/entity-editor";
import { managedEntityKind } from "@/lib/managed-entity";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "পরিচিতি সম্পাদনা" }); }

export default async function ManagedEntityDetailPage({ params }: { params: Promise<{ kind: string; identifier: string }> }) {
  const values = await params, kind = managedEntityKind(values.kind);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(values.identifier)) notFound();
  await requireManagement("books", `/manage/entities/${kind}/${values.identifier}/`);
  let entity: ManagedEntity;
  try { entity = await sessionRequest<ManagedEntity>(`manage/entities/${kind}/${values.identifier}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><EntityNavigation current={kind} /><Link className="text-link" href={`/manage/entities/${kind}/`}><AdminText>{"← তালিকায় ফিরুন"}</AdminText></Link><h1>{entity.name}</h1><p><Link className="button button-quiet" href={`/manage/books/?${new URLSearchParams({ [entityFilters[kind]]: entity.slug, label: entity.name })}`}><Icon name="books" /><AdminText>{"সংশ্লিষ্ট বই দেখুন"}</AdminText></Link></p>
    <EntityEditor key={entity.id} kind={kind} initialEntity={entity} /></>;
}
