import { resolveReaderManifestUrl } from "../reader/manifest.js";

function identity(value) {
  return value;
}

export function buildBookReaderLocation(payload, slug, resolveUrl = identity) {
  const manifestUrl = resolveReaderManifestUrl(payload, resolveUrl);

  if (!manifestUrl) {
    throw new Error("Reader manifest is not available for this book yet.");
  }

  const params = new URLSearchParams();
  if (slug) {
    params.set("slug", slug);
  }
  params.set("manifest", manifestUrl);
  params.set("appNav", "hidden");
  return `/reader?${params.toString()}`;
}

export async function launchBookReader({
  slug,
  apiClient,
  navigate,
  resolveUrl = identity,
}) {
  if (!slug) {
    throw new Error("Missing reader details. Open a book and try again.");
  }
  if (typeof apiClient !== "function") {
    throw new Error("Reader launch is not configured.");
  }

  const payload = await apiClient(`/access/books/${slug}/reader-launch/`, {
    method: "POST",
    body: {},
  });
  navigate(buildBookReaderLocation(payload, slug, resolveUrl));
  return payload;
}
