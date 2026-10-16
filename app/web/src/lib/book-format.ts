import type { BookEditorialUpdate } from "@/api/types";

export function readBookFormat(fields: FormData) {
  const price = String(fields.get("manual_price") ?? "").trim();
  return {
    edition: String(fields.get("edition") ?? ""), manual_language: String(fields.get("manual_language") ?? ""),
    manual_publisher: String(fields.get("manual_publisher") ?? ""), manual_price: price || null,
    manual_binding: String(fields.get("manual_binding") ?? "") as BookEditorialUpdate["manual_binding"],
    manual_is_compilation: fields.has("manual_is_compilation"),
  };
}
