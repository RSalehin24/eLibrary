import { localizeMetadata } from "@/lib/metadata-language";
import { ManagedEntityList } from "@/components/managed-entity-list";
import { managedEntityKind } from "@/lib/managed-entity";
import type { RouteQuery } from "@/lib/route-query";

export async function generateMetadata() { return localizeMetadata({ title: "পরিচিতির তালিকা" }); }

export default async function ManagedEntityListPage({ params, searchParams }: { params: Promise<{ kind: string }>; searchParams: Promise<RouteQuery> }) {
  return <ManagedEntityList kind={managedEntityKind((await params).kind)} parameters={await searchParams} />;
}
