import { cache } from "react";
import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { APIError } from "@/api/http";
import { publicRequest } from "@/api/server";
import type { PublicEntity } from "@/api/types";
import { routeSlug } from "./route-slug";
import { canonicalURL } from "./site";
import { catalogPageNumber, type RouteQuery } from "./route-query";
export { catalogEntityPath } from "./catalog-entity-path";

export type EntityKind = "contributors" | "categories" | "series" | "collections";
export type EntityPageProps = { params: Promise<{ slug: string }>; searchParams: Promise<RouteQuery> };
export const entityLabels: Record<EntityKind, string> = { contributors: "লেখক ও সহযোগী", categories: "বইয়ের বিভাগ", series: "বইয়ের সিরিজ", collections: "সম্পাদকের নির্বাচন" };
export const entityFilters: Record<EntityKind, string> = { contributors: "contributor", categories: "category", series: "series", collections: "collection" };

export const getPublicEntity = cache(async (kind: EntityKind, slug: string) => {
  let entity: PublicEntity;
  try { entity = await publicRequest<PublicEntity>(`catalog/entities/${kind}/${encodeURIComponent(slug)}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  if (entity.slug !== slug) permanentRedirect(`/${kind}/${encodeURIComponent(entity.slug)}/`);
  return entity;
});

export async function entityMetadata(kind: EntityKind, props: EntityPageProps): Promise<Metadata> {
  const entity = await getPublicEntity(kind, routeSlug((await props.params).slug));
  const parameters = await props.searchParams;
  const page = catalogPageNumber(parameters);
  const pathname = `/${kind}/${encodeURIComponent(entity.slug)}/`;
  const canonical = `${pathname}${page > 1 ? `?page=${page}` : ""}`;
  const description = entity.seo_description || entity.editorial_description || `${entity.name} সম্পর্কিত বইয়ের তালিকা।`;
  return { title: entity.seo_title || entity.name, description,
    alternates: { canonical },
    robots: { index: entity.indexable && Object.keys(parameters).every((name) => name === "page"), follow: true },
    openGraph: { title: entity.seo_title || entity.name, description, url: canonicalURL(canonical), locale: "bn_BD",
      ...(entity.social_image_url ? { images: [{ url: entity.social_image_url, alt: entity.name }] } : {}) },
  };
}
