import { sitemapURLs } from "@/lib/sitemap";

export function GET() {
  return sitemapURLs(["/", "/catalog/", "/collections/", "/about/", "/help/", "/contact/"].map((path) => ({ path })));
}
