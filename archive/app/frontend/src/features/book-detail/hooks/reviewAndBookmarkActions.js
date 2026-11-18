export async function deleteBookBookmark({
  apiClient,
  id,
  setBookmarks,
  toast
}) {
  await apiClient(`/access/bookmarks/${id}/`, { method: "DELETE" });
  setBookmarks((current) => current.filter((bookmark) => bookmark.id !== id));
  toast.success("Bookmark removed.");
}

export async function createBookMetadataReview({
  apiClient,
  fetchBook,
  reviewForm,
  setMetadataReviews,
  setReviewForm,
  slug,
  toast
}) {
  const payload = await apiClient(`/catalog/books/${slug}/metadata-reviews/`, {
    method: "POST",
    body: reviewForm
  });
  setMetadataReviews((current) => [payload, ...current]);
  setReviewForm({ state: "pending", notes: "" });
  await fetchBook(slug);
  toast.success("Review saved.");
}

export async function updateBookMetadataReview({
  apiClient,
  fetchBook,
  reviewId,
  setMetadataReviews,
  slug,
  state,
  toast
}) {
  const payload = await apiClient(`/catalog/metadata-reviews/${reviewId}/`, {
    method: "PATCH",
    body: { state }
  });
  setMetadataReviews((current) =>
    current.map((review) => (review.id === reviewId ? payload : review))
  );
  await fetchBook(slug);
  toast.success("Review updated.");
}
