import { notFound, redirect } from "next/navigation";
import { legacyRouteTarget } from "@/lib/legacy-routes";
import { localizeMetadata } from "@/lib/metadata-language";
import type { RouteQuery } from "@/lib/route-query";

export async function generateMetadata() { return localizeMetadata({ robots: { index: false, follow: false } }); }

export default async function LegacyRoutePage({ params, searchParams }: { params: Promise<{ legacy: string }>; searchParams: Promise<RouteQuery> }) {
  const target = legacyRouteTarget((await params).legacy, await searchParams);
  if (!target) notFound();
  redirect(target);
}
