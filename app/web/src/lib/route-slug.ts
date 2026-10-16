import { notFound } from "next/navigation";

export function routeSlug(parameter: string) {
  let slug: string;
  try { slug = decodeURIComponent(parameter); }
  catch { notFound(); }
  if (slug.length > 255 || !/^[\p{L}\p{M}\p{N}_-]+$/u.test(slug)) notFound();
  return slug;
}
