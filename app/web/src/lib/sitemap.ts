import { canonicalURL } from "./site";
import type { SitemapEntry } from "@/api/types";

function escapeXML(value: string) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&apos;");
}

export function sitemapIndex(paths: string[]) {
  const entries = paths.map((path) => `<sitemap><loc>${escapeXML(canonicalURL(path))}</loc></sitemap>`).join("");
  return xmlResponse(`<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${entries}</sitemapindex>`);
}

export function sitemapURLs(paths: { path: string; updatedAt?: string }[]) {
  const entries = paths.map(({ path, updatedAt }) => `<url><loc>${escapeXML(canonicalURL(path))}</loc>${updatedAt ? `<lastmod>${escapeXML(updatedAt)}</lastmod>` : ""}</url>`).join("");
  return xmlResponse(`<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${entries}</urlset>`);
}

export function recordSitemap(kind: string, entries: SitemapEntry[]) {
  return sitemapURLs(entries.map((entry) => ({ path: `/${kind}/${encodeURIComponent(entry.slug)}/`, updatedAt: entry.updated_at })));
}

function xmlResponse(content: string) {
  return new Response(`<?xml version="1.0" encoding="UTF-8"?>${content}`, {
    headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=0, must-revalidate" },
  });
}
