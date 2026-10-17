import { CatalogEntityDirectory } from "@/components/catalog-entity-directory";
import { localizeMetadata } from "@/lib/metadata-language";
import { entityLabels } from "@/lib/catalog-entity";
import type { RouteQuery } from "@/lib/route-query";

export async function generateMetadata() { return localizeMetadata({ title: entityLabels.categories }); }

export default async function DirectoryPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  return <CatalogEntityDirectory kind="categories" parameters={await searchParams} />;
}
