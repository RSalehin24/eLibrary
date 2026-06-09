import { useRef, useState } from "react";
import { bookDetailFetch } from "../api";
import {
  regenerateBookAsset,
  replaceBookEpub,
  sendBookToKindle
} from "./assetMutationActions";
import { downloadBookAsset } from "./assetPreviewActions";

export function useBookAssetActions({
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
}) {
  const epubInputRef = useRef(null);
  const [assetLoadingCounts, setAssetLoadingCounts] = useState({});
  const [pickingEpub, setPickingEpub] = useState(false);
  const [replacingEpub, setReplacingEpub] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [sendingToKindle, setSendingToKindle] = useState(false);

  function clearAssetLoading(assetId) {
    setAssetLoadingCounts((current) => {
      const nextCount = (current[assetId] || 1) - 1;
      if (nextCount > 0) {
        return {
          ...current,
          [assetId]: nextCount
        };
      }
      const { [assetId]: _removed, ...rest } = current;
      return rest;
    });
  }

  function openEpubPicker() {
    if (pickingEpub || replacingEpub || regenerating || detail.hasActiveProcessing) {
      return;
    }
    setPickingEpub(true);
    const handleFocusBack = () => {
      setPickingEpub(false);
      window.removeEventListener("focus", handleFocusBack);
    };
    window.addEventListener("focus", handleFocusBack);
    epubInputRef.current?.click();
  }

  async function replaceEpub(event) {
    const file = event.target.files?.[0];
    if (!file) {
      setPickingEpub(false);
      return;
    }

    try {
      setPickingEpub(false);
      setReplacingEpub(true);
      await replaceBookEpub({
        apiClient: bookDetailFetch,
        event,
        replaceBookRoute,
        setBook,
        slug,
        toast
      });
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      event.target.value = "";
      setReplacingEpub(false);
      setPickingEpub(false);
    }
  }

  async function regenerateBook() {
    if (!book || regenerating || detail.hasActiveProcessing) {
      return;
    }

    try {
      setRegenerating(true);
      await regenerateBookAsset({
        apiClient: bookDetailFetch,
        replaceBookRoute,
        setBook,
        slug,
        toast
      });
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setRegenerating(false);
    }
  }

  async function downloadAsset(asset) {
    if (!asset?.download_url) {
      return;
    }

    setAssetLoadingCounts((current) => ({
      ...current,
      [asset.id]: (current[asset.id] || 0) + 1
    }));

    try {
      await downloadBookAsset({
        asset,
        book,
        htmlPreviewLockedByAssetId,
        setHtmlPreviewLockedByAssetId,
        slug,
        toast,
        user
      });
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      clearAssetLoading(asset.id);
    }
  }

  async function sendToKindle() {
    if (!book || !detail.epubAsset || sendingToKindle) {
      return;
    }

    try {
      setSendingToKindle(true);
      await sendBookToKindle({
        apiClient: bookDetailFetch,
        slug,
        toast
      });
      const updated = await fetchBook(slug);
      if (updated) {
        setBook(updated);
      }
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setSendingToKindle(false);
    }
  }

  return {
    assetLoadingCounts,
    downloadAsset,
    epubInputRef,
    openEpubPicker,
    pickingEpub,
    regenerateBook,
    regenerating,
    replaceEpub,
    replacingEpub,
    sendToKindle,
    sendingToKindle
  };
}
