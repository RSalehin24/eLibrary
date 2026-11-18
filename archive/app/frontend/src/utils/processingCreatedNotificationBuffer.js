export const CREATED_NOTIFICATION_INTERVAL_MS = 3 * 60 * 1000;

export function createdNotificationDescription(count) {
  return count === 1 ? "1 book created." : `${count} books created.`;
}

export function createCreatedNotificationBuffer({
  intervalMs = CREATED_NOTIFICATION_INTERVAL_MS,
  onFlush = () => {},
  schedule = (callback, delay) => window.setTimeout(callback, delay),
  clear = (timerId) => window.clearTimeout(timerId),
} = {}) {
  let pendingCount = 0;
  let timerId = null;

  function clearTimer() {
    if (!timerId) {
      return;
    }
    clear(timerId);
    timerId = null;
  }

  function flushIfPending() {
    if (!pendingCount) {
      clearTimer();
      return 0;
    }

    const completedCount = pendingCount;
    pendingCount = 0;
    clearTimer();
    onFlush(completedCount);
    return completedCount;
  }

  function scheduleFlush() {
    if (timerId || pendingCount <= 0) {
      return;
    }

    timerId = schedule(() => {
      flushIfPending();
    }, intervalMs);
  }

  function addCompletedCount(count) {
    const parsed = Number(count);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return pendingCount;
    }

    pendingCount += parsed;
    scheduleFlush();
    return pendingCount;
  }

  function getPendingCount() {
    return pendingCount;
  }

  function destroy() {
    pendingCount = 0;
    clearTimer();
  }

  return {
    addCompletedCount,
    flushIfPending,
    getPendingCount,
    destroy,
  };
}
