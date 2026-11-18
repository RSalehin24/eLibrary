export function bindDoubleTapToggle({
  element,
  onToggle,
  isInteractiveTarget,
  setLastGlobalTouchTime,
  getLastGlobalTouchTime,
}) {
  if (!element) return;

  const DOUBLE_TAP_DELAY = 300;
  const ownerDocument = element.ownerDocument || document;
  const ownerWindow = ownerDocument.defaultView || window;

  let startX = 0;
  let startY = 0;
  let lastTapTime = 0;
  let lastTouchEndTime = 0;
  let isMultiTouchGesture = false;

  const getActiveSelection = () =>
    ownerWindow?.getSelection?.() ||
    ownerDocument?.getSelection?.() ||
    window.getSelection?.() ||
    null;

  const hasActiveTextSelection = () => {
    const selection = getActiveSelection();
    if (!selection || selection.rangeCount === 0) return false;
    if (selection.isCollapsed) return false;
    return (selection.toString?.() || "").trim().length > 0;
  };

  const clearSelection = () => {
    const selection = getActiveSelection();
    if (selection?.rangeCount) {
      selection.removeAllRanges();
    }
  };

  const onTouchStart = (event) => {
    if (event.touches && event.touches.length > 1) {
      isMultiTouchGesture = true;
      return;
    }

    const touch = event.changedTouches && event.changedTouches[0];
    if (!touch) return;

    isMultiTouchGesture = false;
    startX = touch.clientX;
    startY = touch.clientY;
  };

  const onTouchEnd = (event) => {
    if (isMultiTouchGesture) {
      if (!event.touches || event.touches.length === 0) {
        isMultiTouchGesture = false;
      }
      return;
    }

    const touch = event.changedTouches && event.changedTouches[0];
    if (!touch) return;

    const deltaX = Math.abs(touch.clientX - startX);
    const deltaY = Math.abs(touch.clientY - startY);
    if (deltaX > 12 || deltaY > 12) return;

    if (isInteractiveTarget?.(event.target)) return;
    // Don't toggle the UI / clear selection while the user is interacting with a text selection.
    if (hasActiveTextSelection()) {
      lastTapTime = 0;
      return;
    }

    const now = Date.now();
    lastTouchEndTime = now;
    const timeSinceLastTap = now - lastTapTime;

    if (timeSinceLastTap < DOUBLE_TAP_DELAY && timeSinceLastTap > 0) {
      if (event.cancelable) {
        event.preventDefault();
      }
      clearSelection();
      setLastGlobalTouchTime?.(now);
      onToggle?.();
      lastTapTime = 0;
      return;
    }

    lastTapTime = now;
  };

  const onClick = (event) => {
    if (Date.now() - lastTouchEndTime < 400) return;
    if (Date.now() - (getLastGlobalTouchTime?.() || 0) < 400) return;
    if (isInteractiveTarget?.(event.target)) return;
    // Preserve user text selections so the highlight toolbar (and copy) can act on them.
    if (hasActiveTextSelection()) {
      lastTapTime = 0;
      return;
    }

    if (event.cancelable) {
      event.preventDefault();
    }
    clearSelection();

    const now = Date.now();
    const timeSinceLastClick = now - lastTapTime;

    if (timeSinceLastClick < DOUBLE_TAP_DELAY && timeSinceLastClick > 0) {
      onToggle?.();
      lastTapTime = 0;
    } else {
      lastTapTime = now;
    }
  };

  const onDoubleClick = (event) => {
    if (Date.now() - lastTouchEndTime < 400) return;
    if (Date.now() - (getLastGlobalTouchTime?.() || 0) < 400) return;
    if (isInteractiveTarget?.(event.target)) return;
    // A double-click commonly selects a word — keep the selection intact.
    if (hasActiveTextSelection()) return;

    if (event.cancelable) {
      event.preventDefault();
    }
    clearSelection();
  };

  const existingTouchStart = element.__readerModeTouchStartHandler;
  const existingTouchEnd = element.__readerModeTouchEndHandler;
  const existingClick = element.__readerModeClickHandler;
  const existingDoubleClick = element.__readerModeDblClickHandler;

  if (existingTouchStart) {
    element.removeEventListener("touchstart", existingTouchStart);
  }
  if (existingTouchEnd) {
    element.removeEventListener("touchend", existingTouchEnd);
  }
  if (existingClick) {
    element.removeEventListener("click", existingClick);
  }
  if (existingDoubleClick) {
    element.removeEventListener("dblclick", existingDoubleClick);
  }

  element.__readerModeTouchStartHandler = onTouchStart;
  element.__readerModeTouchEndHandler = onTouchEnd;
  element.__readerModeClickHandler = onClick;
  element.__readerModeDblClickHandler = onDoubleClick;

  element.addEventListener("touchstart", onTouchStart, { passive: true });
  element.addEventListener("touchend", onTouchEnd, { passive: false });
  element.addEventListener("click", onClick);
  element.addEventListener("dblclick", onDoubleClick);
}
