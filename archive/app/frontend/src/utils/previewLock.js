const PREVIEW_LOCK_PREFIX = "ebook_preview_lock:";
const PREVIEW_LOCK_TTL_MS = 15000;

function safeJsonParse(rawValue) {
  if (!rawValue) {
    return null;
  }
  try {
    return JSON.parse(rawValue);
  } catch {
    return null;
  }
}

function nowMs() {
  return Date.now();
}

export function isPreviewLockActive(lockValue, now = nowMs()) {
  if (!lockValue || typeof lockValue !== "object") {
    return false;
  }
  if (!lockValue.tabId || typeof lockValue.ts !== "number") {
    return false;
  }
  return now - lockValue.ts <= PREVIEW_LOCK_TTL_MS;
}

export function getPreviewLockKey(previewUrl) {
  if (!previewUrl) {
    return "";
  }
  try {
    const parsedUrl = new URL(previewUrl, window.location.origin);
    return `${PREVIEW_LOCK_PREFIX}${parsedUrl.pathname}`;
  } catch {
    return "";
  }
}

export function getActivePreviewLock(lockKey) {
  if (!lockKey) {
    return null;
  }
  const lockValue = safeJsonParse(window.localStorage.getItem(lockKey));
  if (!isPreviewLockActive(lockValue)) {
    return null;
  }
  return lockValue;
}

export function isPreviewLocked(lockKey) {
  return Boolean(getActivePreviewLock(lockKey));
}
