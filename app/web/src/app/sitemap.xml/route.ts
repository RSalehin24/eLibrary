import { publicRequest } from "@/api/server";
import type { SitemapBatch } from "@/api/types";
import { sitemapIndex } from "@/lib/sitemap";

export const dynamic = "force-dynamic";

export async function GET() {
  const batches = await publicRequest<SitemapBatch[]>("catalog/sitemaps/");
  const paths = batches.flatMap((batch) => Array.from({ length: batch.pages }, (_, index) => `/sitemap-records.xml?kind=${batch.kind}&page=${index + 1}`));
  return sitemapIndex(["/sitemap-static.xml", ...paths]);
}
