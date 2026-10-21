import { CatalogEntityDirectory } from "@/components/catalog-entity-directory";
import { localizeMetadata } from "@/lib/metadata-language";
import { catalogPageNumber, type RouteQuery } from "@/lib/route-query";

type Props = { searchParams: Promise<RouteQuery> };

export async function generateMetadata({ searchParams }: Props) {
  const parameters = await searchParams, page = catalogPageNumber(parameters);
  return localizeMetadata({ title: "পাঠতালিকা", alternates: { canonical: `/collections/${page > 1 ? `?page=${page}` : ""}` }, robots: { index: Object.keys(parameters).every(name => name === "page"), follow: true } });
}

export default async function CollectionsPage({ searchParams }: Props) {
  return <CatalogEntityDirectory kind="collections" parameters={await searchParams} />;
}
