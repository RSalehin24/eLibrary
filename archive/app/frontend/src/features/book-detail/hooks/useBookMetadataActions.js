import { useState } from "react";
import { bookDetailFetch } from "../api";
import { saveBookMetadata } from "./metadataActions";
import {
  createBookMetadataReview,
  deleteBookBookmark,
  updateBookMetadataReview
} from "./reviewAndBookmarkActions";

export function useBookMetadataActions({
  editor,
  fetchBook,
  refreshMetadataCollections,
  replaceBookRoute,
  reviewForm,
  setBook,
  setBookmarks,
  setMetadataReviews,
  setReviewForm,
  slug,
  toast
}) {
  const [savingMetadata, setSavingMetadata] = useState(false);
  const [savingReview, setSavingReview] = useState(false);
  const [reviewUpdating, setReviewUpdating] = useState({ id: "", state: "" });
  const [deletingBookmarkId, setDeletingBookmarkId] = useState("");

  async function saveMetadata(event) {
    event.preventDefault();
    if (savingMetadata) {
      return;
    }

    try {
      setSavingMetadata(true);
      await saveBookMetadata({
        apiClient: bookDetailFetch,
        editor,
        refreshMetadataCollections,
        replaceBookRoute,
        setBook,
        slug,
        toast
      });
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setSavingMetadata(false);
    }
  }

  async function deleteBookmark(id) {
    if (deletingBookmarkId) {
      return;
    }

    try {
      setDeletingBookmarkId(id);
      await deleteBookBookmark({
        apiClient: bookDetailFetch,
        id,
        setBookmarks,
        toast
      });
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setDeletingBookmarkId("");
    }
  }

  async function createMetadataReview(event) {
    event.preventDefault();
    if (savingReview) {
      return;
    }

    try {
      setSavingReview(true);
      await createBookMetadataReview({
        apiClient: bookDetailFetch,
        fetchBook,
        reviewForm,
        setMetadataReviews,
        setReviewForm,
        slug,
        toast
      });
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setSavingReview(false);
    }
  }

  async function updateMetadataReview(reviewId, state) {
    if (reviewUpdating.id) {
      return;
    }

    try {
      setReviewUpdating({ id: reviewId, state });
      await updateBookMetadataReview({
        apiClient: bookDetailFetch,
        fetchBook,
        reviewId,
        setMetadataReviews,
        slug,
        state,
        toast
      });
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setReviewUpdating({ id: "", state: "" });
    }
  }

  return {
    createMetadataReview,
    deleteBookmark,
    deletingBookmarkId,
    reviewUpdating,
    savingMetadata,
    savingReview,
    saveMetadata,
    updateMetadataReview
  };
}
