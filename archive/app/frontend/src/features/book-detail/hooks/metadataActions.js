function parseMetadataList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseContributors(value) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, role = "author"] = line.split("|").map((part) => part.trim());
      return { name, role: role || "author" };
    });
}

export async function saveBookMetadata({
  apiClient,
  editor,
  refreshMetadataCollections,
  replaceBookRoute,
  setBook,
  slug,
  toast
}) {
  const payload = await apiClient(`/catalog/books/${slug}/metadata/`, {
    method: "PATCH",
    body: {
      title: editor.title,
      summary: editor.summary,
      contributors: parseContributors(editor.contributors),
      series: parseMetadataList(editor.series),
      categories: parseMetadataList(editor.categories),
      notes: editor.notes
    }
  });

  setBook(payload);
  if (payload.slug && payload.slug !== slug) {
    replaceBookRoute(payload.slug);
  }
  await refreshMetadataCollections(payload.slug || slug);
  toast.success("Metadata updated.");
}
