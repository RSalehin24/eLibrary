const MAX_PENDING_EXPORT_AGE_MS = 10 * 60 * 1000;

function storage() {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function readPendingExport(key) {
  const sessionStorage = storage();
  if (!sessionStorage) {
    return null;
  }

  try {
    const rawValue = sessionStorage.getItem(key);
    if (!rawValue) {
      return null;
    }

    const payload = JSON.parse(rawValue);
    const startedAt = Number(payload?.startedAt || 0);
    if (!payload?.mode || !Array.isArray(payload?.items)) {
      sessionStorage.removeItem(key);
      return null;
    }

    if (!startedAt || Date.now() - startedAt > MAX_PENDING_EXPORT_AGE_MS) {
      sessionStorage.removeItem(key);
      return null;
    }

    return payload;
  } catch {
    sessionStorage.removeItem(key);
    return null;
  }
}

export function writePendingExport(key, payload) {
  const sessionStorage = storage();
  const nextPayload = {
    ...payload,
    startedAt: Date.now()
  };

  if (!sessionStorage) {
    return nextPayload;
  }

  try {
    sessionStorage.setItem(key, JSON.stringify(nextPayload));
  } catch {
    return nextPayload;
  }

  return nextPayload;
}

export function clearPendingExport(key) {
  const sessionStorage = storage();
  if (!sessionStorage) {
    return;
  }

  try {
    sessionStorage.removeItem(key);
  } catch {
    // Ignore storage cleanup failures.
  }
}
