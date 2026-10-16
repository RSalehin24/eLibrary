import { APIError } from "@/api/http";
import { publicRequest } from "@/api/server";
import type { SitemapEntry } from "@/api/types";
import { recordSitemap } from "@/lib/sitemap";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const parameters = new URL(request.url).searchParams;
  const kind = parameters.get("kind") ?? "";
  const page = parameters.get("page") ?? "";
  if (parameters.size !== 2 || parameters.getAll("kind").length !== 1 || parameters.getAll("page").length !== 1) return new Response(null, { status: 404 });
  if (!["books", "contributors", "categories", "series", "collections"].includes(kind) || !/^[1-9]\d{0,5}$/.test(page)) return new Response(null, { status: 404 });
  try {
    const entries = await publicRequest<SitemapEntry[]>(`catalog/sitemaps/${kind}/${page}/`);
    return recordSitemap(kind, entries);
  } catch (error) {
    if (error instanceof APIError && error.status === 404) return new Response(null, { status: 404 });
    throw error;
  }
}
