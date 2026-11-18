import { getPreviewLockKey, isPreviewLocked } from "../../../utils/previewLock";
import { resolveBookDetailUrl } from "../api";
import { openManagedPreviewWindow, waitForMinimumLoader, waitForUiFrame } from "../utils";

const previewWindows = new Map();

function getPreviewKey({ book, slug, user }) {
  return `${user?.id || "anon"}:${book?.id || slug}`;
}

function focusExistingPreview({ book, slug, user }) {
  const previewKey = getPreviewKey({ book, slug, user });
  const existingWindow = previewWindows.get(previewKey);
  if (existingWindow && !existingWindow.closed) {
    existingWindow.focus();
    return true;
  }
  return false;
}

function openHtmlPreview({
  asset,
  book,
  previewUrl,
  setHtmlPreviewLockedByAssetId,
  slug,
  toast,
  user
}) {
  if (focusExistingPreview({ book, slug, user })) {
    toast.info("Preview is already open for this book.");
    return;
  }

  const previewKey = getPreviewKey({ book, slug, user });
  const target = `html_preview_${user?.id || "anon"}_${book?.id || slug}`;
  const openedWindow = openManagedPreviewWindow(previewUrl, target);
  if (!openedWindow) {
    toast.error("Preview window could not be opened. Please allow popups.");
    return;
  }

  previewWindows.set(previewKey, openedWindow);
  openedWindow.focus();
  setHtmlPreviewLockedByAssetId((current) => ({
    ...current,
    [asset.id]: true
  }));
}

export async function downloadBookAsset({
  asset,
  book,
  htmlPreviewLockedByAssetId,
  setHtmlPreviewLockedByAssetId,
  slug,
  toast,
  user
}) {
  if (!asset?.download_url) return;

  if (asset.asset_type === "html" && htmlPreviewLockedByAssetId[asset.id]) {
    focusExistingPreview({ book, slug, user });
    toast.info("Preview is already open for this book.");
    return;
  }

  const startedAt = Date.now();
  await waitForUiFrame();
  const previewUrl = resolveBookDetailUrl(asset.download_url);

  if (asset.asset_type !== "html") {
    window.open(previewUrl, "_blank", "noopener,noreferrer");
    await waitForMinimumLoader(startedAt, 420);
    return;
  }

  const lockKey = getPreviewLockKey(previewUrl);
  if (lockKey && isPreviewLocked(lockKey)) {
    toast.info("Preview is already open for this book.");
    return;
  }

  openHtmlPreview({
    asset,
    book,
    previewUrl,
    setHtmlPreviewLockedByAssetId,
    slug,
    toast,
    user
  });
  await waitForMinimumLoader(startedAt, 420);
}
