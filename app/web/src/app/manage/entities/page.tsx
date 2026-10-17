import { localizeMetadata } from "@/lib/metadata-language";
import { ManagedEntityList } from "@/components/managed-entity-list";
import type { RouteQuery } from "@/lib/route-query";

export async function generateMetadata() { return localizeMetadata({ title: "লেখক ও বিভাগ" }); }

export default async function ManagedEntitiesPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  return <ManagedEntityList kind="contributors" parameters={await searchParams} />;
}
