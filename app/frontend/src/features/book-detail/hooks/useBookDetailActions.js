import { useBookAssetActions } from "./useBookAssetActions";
import { useBookLifecycleActions } from "./useBookLifecycleActions";
import { useBookMetadataActions } from "./useBookMetadataActions";
import { useBookOwnershipActions } from "./useBookOwnershipActions";
import { useBookReaderAction } from "./useBookReaderAction";

export function useBookDetailActions({
  book,
  currentDetailPath,
  detail,
  editor,
  fetchBook,
  htmlPreviewLockedByAssetId,
  navigate,
  refreshMetadataCollections,
  replaceBookRoute,
  returnTarget,
  reviewForm,
  setBook,
  setBookmarks,
  setHtmlPreviewLockedByAssetId,
  setMetadataReviews,
  setReviewForm,
  slug,
  toast,
  user
}) {
  const readerActions = useBookReaderAction({ navigate, slug, toast });
  const ownershipActions = useBookOwnershipActions({
    book,
    setBook,
    slug,
    toast
  });
  const lifecycleActions = useBookLifecycleActions({
    book,
    currentDetailPath,
    detail,
    navigate,
    returnTarget,
    slug,
    toast
  });
  const metadataActions = useBookMetadataActions({
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
  });
  const assetActions = useBookAssetActions({
    book,
    detail,
    fetchBook,
    htmlPreviewLockedByAssetId,
    replaceBookRoute,
    setBook,
    setHtmlPreviewLockedByAssetId,
    slug,
    toast,
    user
  });

  return {
    ...assetActions,
    ...lifecycleActions,
    ...metadataActions,
    ...ownershipActions,
    ...readerActions
  };
}
