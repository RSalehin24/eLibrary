export function readBookFormat(fields: FormData) {
  return {
    edition: String(fields.get("edition") ?? ""),
    language: String(fields.get("language") ?? ""),
    publisher: String(fields.get("publisher") ?? ""),
    is_compilation: fields.has("is_compilation"),
  };
}
