export async function replaceBookEpub({
  apiClient,
  event,
  replaceBookRoute,
  setBook,
  slug,
  toast
}) {
  const file = event.target.files?.[0];
  if (!file) return false;

  const formData = new FormData();
  formData.append("file", file);
  const payload = await apiClient(`/catalog/books/${slug}/assets/epub/`, {
    method: "POST",
    body: formData
  });
  setBook(payload);
  if (payload.slug && payload.slug !== slug) {
    replaceBookRoute(payload.slug);
  }
  toast.success("EPUB updated.");
  return true;
}

export async function regenerateBookAsset({
  apiClient,
  replaceBookRoute,
  setBook,
  slug,
  toast
}) {
  const payload = await apiClient(`/catalog/books/${slug}/regenerate/`, {
    method: "POST",
    body: {}
  });
  if (payload.book) {
    setBook(payload.book);
    if (payload.book.slug && payload.book.slug !== slug) {
      replaceBookRoute(payload.book.slug);
    }
  }

  if (!payload.created) {
    toast.success("Book regeneration is already in progress.");
  } else if (payload.job?.status === "succeeded") {
    toast.success("Book regenerated.");
  } else {
    toast.success("Book regeneration started.");
  }
}

export async function sendBookToKindle({ apiClient, slug, toast }) {
  const payload = await apiClient(`/access/books/${slug}/send-to-kindle/`, {
    method: "POST",
    body: {}
  });
  toast.success(payload?.detail || "Sent to Kindle.");
}
