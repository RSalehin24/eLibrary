import { redirect } from "next/navigation";
import { legacyRouteTarget } from "@/lib/legacy-routes";
import { localizeMetadata } from "@/lib/metadata-language";
import type { RouteQuery } from "@/lib/route-query";

export async function generateMetadata() { return localizeMetadata({ title: "বই পড়ুন", robots: { index: false, follow: false } }); }

export default async function LegacyReaderPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  redirect(legacyRouteTarget("reader", await searchParams) ?? "/my-books/");
}
