import { useEffect, useState } from "react";
import { resolveBookDetailUrl } from "../api";
import { getPreviewLockKey, isPreviewLocked } from "../../../utils/previewLock";


export function useHtmlPreviewLockState(book) {
  const [htmlPreviewLockedByAssetId, setHtmlPreviewLockedByAssetId] = useState({});

  useEffect(() => {
    const htmlAssets = (book?.assets || []).filter(
      (asset) => asset.asset_type === "html" && asset.download_url,
    );
    if (!htmlAssets.length) {
      setHtmlPreviewLockedByAssetId({});
      return undefined;
    }

    function syncPreviewLocks() {
      setHtmlPreviewLockedByAssetId(
        htmlAssets.reduce((nextState, asset) => {
          const previewUrl = resolveBookDetailUrl(asset.download_url);
          const lockKey = getPreviewLockKey(previewUrl);
          nextState[asset.id] = lockKey ? isPreviewLocked(lockKey) : false;
          return nextState;
        }, {}),
      );
    }

    syncPreviewLocks();
    const intervalId = window.setInterval(syncPreviewLocks, 1500);

    const onStorage = (event) => {
      if (!event.key || !event.key.startsWith("ebook_preview_lock:")) {
        return;
      }
      syncPreviewLocks();
    };

    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", syncPreviewLocks);
    document.addEventListener("visibilitychange", syncPreviewLocks);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", syncPreviewLocks);
      document.removeEventListener("visibilitychange", syncPreviewLocks);
    };
  }, [book?.id, book?.assets]);

  return {
    htmlPreviewLockedByAssetId,
    setHtmlPreviewLockedByAssetId,
  };
}

