import { useState } from "react";
import { bookDetailFetch } from "../api";

export function useBookLifecycleActions({
  book,
  currentDetailPath,
  detail,
  navigate,
  returnTarget,
  slug,
  toast
}) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  function requestDeleteBook() {
    if (!book || deleting || detail.hasActiveProcessing) {
      return;
    }
    setDeleteDialogOpen(true);
  }

  async function confirmDeleteBook() {
    if (!book || deleting || detail.hasActiveProcessing) {
      return;
    }

    try {
      setDeleting(true);
      await bookDetailFetch(`/catalog/books/${slug}/`, { method: "DELETE" });
      toast.success("Book deleted.");
      navigate(
        returnTarget && returnTarget !== currentDetailPath
          ? returnTarget
          : "/library",
        { replace: true }
      );
    } catch (nextError) {
      toast.error(nextError.message);
      setDeleting(false);
    }
  }

  return {
    confirmDeleteBook,
    deleteDialogOpen,
    deleting,
    requestDeleteBook,
    setDeleteDialogOpen
  };
}
