import { CatalogBrowseNav } from "@/components/catalog-browse-nav";
import { SiteText } from "@/components/site-language";
import { localizeMetadata } from "@/lib/metadata-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { publicRequest } from "@/api/server";
import type { EntityCollection } from "@/api/types";
import { CatalogPagination } from "@/components/catalog-pagination";
import { catalogPageNumber, type RouteQuery } from "@/lib/route-query";

type CollectionPageProps = { searchParams: Promise<RouteQuery> };

export async function generateMetadata({ searchParams }: CollectionPageProps) {
  const parameters = await searchParams;
  const page = catalogPageNumber(parameters);
  return localizeMetadata({ title: "সম্পাদকের নির্বাচন", description: "বাংলা বইয়ের পর্যালোচিত পাঠতালিকা ও সম্পাদকীয় সংগ্রহ।",
    alternates: { canonical: `/collections/${page > 1 ? `?page=${page}` : ""}` },
    robots: { index: Object.keys(parameters).every((name) => name === "page"), follow: true } });
}

export default async function CollectionsPage({ searchParams }: CollectionPageProps) {
  const page = catalogPageNumber(await searchParams);
  const collections = await publicRequest<EntityCollection>(`catalog/collections/?page=${page}`);
  if (page > 1 && !collections.entries.length) notFound();
  return <><CatalogBrowseNav current="/collections/" /><header className="page-title"><p className="eyebrow"><SiteText>{"এক বিষয়, অনেক বই"}</SiteText></p><h1><SiteText>{"সম্পাদকের নির্বাচন"}</SiteText></h1>
    <p className="book-description"><SiteText>{"পর্যালোচিত বই একসঙ্গে খুঁজে নিন। প্রতিটি সংগ্রহের পরিচিতিতে বই বাছাইয়ের বিষয় ও পাঠের প্রেক্ষাপট জানুন।"}</SiteText></p></header>
    <ul className="management-list">{collections.entries.map((collection) => <li key={collection.id}><h2>
      <Link className="text-link" href={`/collections/${encodeURIComponent(collection.slug)}/`}>{collection.name}</Link></h2></li>)}</ul>
    {!collections.entries.length && <p className="empty-state"><SiteText>{"পর্যালোচনা শেষে নির্বাচিত সংগ্রহ এখানে প্রকাশিত হবে।"}</SiteText></p>}
    <CatalogPagination pathname="/collections/" page={page} hasMore={collections.has_more} /></>;
}
