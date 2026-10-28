type LegacyQuery = Record<string, string | string[] | undefined>;

export function legacyRouteTarget(route: string, parameters: LegacyQuery): string | null {
  if (route !== "reader") return null;
  const slug = parameters.slug;
  if (typeof slug !== "string" || slug.length > 255 || !/^[\p{L}\p{M}\p{N}_-]+$/u.test(slug)) return "/my-books/";
  return `/my-books/${encodeURIComponent(slug)}/`;
}
