import type { BookEditorialUpdate } from "@/api/types";

export type EditorialValues = Required<Pick<BookEditorialUpdate, "editorial_description" | "alternative_names" | "seo_title" | "seo_description" | "social_image_url" | "indexing_eligible">>;

export const emptyEditorial: EditorialValues = { editorial_description: "", alternative_names: [], seo_title: "", seo_description: "", social_image_url: "", indexing_eligible: false };

export function readEditorialFields(fields: FormData): EditorialValues {
  return { editorial_description: String(fields.get("editorial_description") ?? ""),
    alternative_names: String(fields.get("alternative_names") ?? "").split("\n").map((name) => name.trim()).filter(Boolean),
    seo_title: String(fields.get("seo_title") ?? ""), seo_description: String(fields.get("seo_description") ?? ""),
    social_image_url: String(fields.get("social_image_url") ?? ""), indexing_eligible: fields.has("indexing_eligible") };
}
