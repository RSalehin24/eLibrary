const DEFAULT_TOAST_COPY = {
  success: {
    title: "Success",
    description: "The action completed.",
  },
  error: {
    title: "Something went wrong",
    description: "Please try again.",
  },
  info: {
    title: "Notice",
    description: "",
  },
};

export const DEFAULT_TOAST_TIMEOUT_MS = 3600;

function cleanToastText(value) {
  return typeof value === "string" ? value.trim() : "";
}

function resolveToastTimeout(input) {
  const duration = Number(input?.holdOpenMs);
  if (Number.isFinite(duration) && duration > 0) {
    return duration;
  }
  return DEFAULT_TOAST_TIMEOUT_MS;
}

function buildToastId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function normalizeToast(input, fallbackType = "info") {
  const defaults = DEFAULT_TOAST_COPY[fallbackType] || DEFAULT_TOAST_COPY.info;

  if (typeof input === "string") {
    return {
      title: defaults.title,
      description: cleanToastText(input) || defaults.description,
      type: fallbackType,
      soundType: fallbackType,
    };
  }

  const title = cleanToastText(input?.title || input?.message);
  const description = cleanToastText(input?.description);
  const soundType = cleanToastText(input?.soundType || input?.type || fallbackType);

  return {
    title: title || defaults.title,
    description: description || (!title ? defaults.description : ""),
    type: input?.type || fallbackType,
    soundType: soundType || fallbackType,
  };
}

export function createToastManager({
  schedule = (callback, delay) => window.setTimeout(callback, delay),
  clear = (timerId) => window.clearTimeout(timerId),
  createId = buildToastId,
  playSound = () => {},
  initialMuted = false,
} = {}) {
  const timers = new Map();
  const groupedToastIds = new Map();
  const listeners = new Set();
  let muted = Boolean(initialMuted);
  let toasts = [];

  function getState() {
    return {
      toasts: [...toasts],
      muted,
    };
  }

  function emit() {
    const snapshot = getState();
    listeners.forEach((listener) => listener(snapshot));
  }

  function clearTimer(id) {
    const timerId = timers.get(id);
    if (timerId) {
      clear(timerId);
      timers.delete(id);
    }
  }

  function dismiss(id) {
    clearTimer(id);
    const nextToast = toasts.find((toast) => toast.id === id);
    if (nextToast?.groupKey) {
      groupedToastIds.delete(nextToast.groupKey);
    }
    toasts = toasts.filter((toast) => toast.id !== id);
    emit();
  }

  function scheduleDismiss(id, duration) {
    clearTimer(id);
    const timerId = schedule(() => dismiss(id), duration);
    timers.set(id, timerId);
  }

  function push(input, fallbackType = "info") {
    const normalized = normalizeToast(input, fallbackType);
    const duration = resolveToastTimeout(input);
    const groupKey = cleanToastText(input?.groupKey);
    const existingId = groupKey ? groupedToastIds.get(groupKey) : "";

    if (existingId) {
      toasts = toasts.map((toast) =>
        toast.id === existingId
          ? {
              ...toast,
              ...normalized,
              id: existingId,
              groupKey,
            }
          : toast,
      );
      scheduleDismiss(existingId, duration);
      emit();
      return existingId;
    }

    const nextToast = {
      id: createId(),
      ...normalized,
      ...(groupKey ? { groupKey } : {}),
    };

    toasts = [...toasts, nextToast];
    if (groupKey) {
      groupedToastIds.set(groupKey, nextToast.id);
    }
    scheduleDismiss(nextToast.id, duration);
    emit();

    if (!muted) {
      playSound(nextToast.soundType || nextToast.type);
    }

    return nextToast.id;
  }

  function setMuted(value) {
    muted = Boolean(value);
    emit();
    return muted;
  }

  function toggleMuted() {
    return setMuted(!muted);
  }

  function subscribe(listener) {
    listeners.add(listener);
    listener(getState());
    return () => {
      listeners.delete(listener);
    };
  }

  function destroy() {
    timers.forEach((timerId) => clear(timerId));
    timers.clear();
    groupedToastIds.clear();
    listeners.clear();
    toasts = [];
  }

  return {
    dismiss,
    destroy,
    getState,
    push,
    setMuted,
    subscribe,
    toggleMuted,
  };
}
