import { catalogFetch } from "../../api/catalog";

export async function loadManualBookOptions() {
  const [
    categoryPayload,
    writerPayload,
    translatorPayload,
    editorPayload,
    seriesPayload,
    publisherPayload
  ] = await Promise.all([
    catalogFetch("/catalog/categories/?record_type=all&sort=name"),
    catalogFetch("/catalog/writers/?record_type=all&sort=name"),
    catalogFetch("/catalog/translators/?record_type=all&sort=name"),
    catalogFetch("/catalog/editors/?record_type=all&sort=name"),
    catalogFetch("/catalog/series/?record_type=all&sort=name"),
    catalogFetch("/catalog/publishers/?record_type=all&sort=name")
  ]);

  return {
    categories: categoryPayload.map((entry) => entry.name),
    contributors: mergeContributorSuggestions([
      writerPayload,
      translatorPayload,
      editorPayload
    ]),
    series: seriesPayload.map((entry) => entry.name),
    publishers: publisherPayload.map((entry) => entry.name)
  };
}

export function mergeContributorSuggestions(payloads) {
  const seen = new Set();
  const names = [];

  payloads.flat().forEach((entry) => {
    const name = (entry?.name || "").trim();
    const normalizedName = name.toLowerCase();
    if (!normalizedName || seen.has(normalizedName)) {
      return;
    }
    seen.add(normalizedName);
    names.push(name);
  });

  return names.sort((left, right) => left.localeCompare(right));
}
