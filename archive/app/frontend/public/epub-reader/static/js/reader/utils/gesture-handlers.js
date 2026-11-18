export function createSwipeBinder({
  onNext,
  onPrev,
  onChangeFontSize,
  onCycleTheme
}) {
  const swipeThresholdNext = 90;
  const swipeThresholdPrev = 100;
  const timeLimit = 600;
  const pinchThreshold = 24;
  const twoFingerTapMaxDuration = 260;
  const twoFingerTapMaxTravel = 24;
  const twoFingerTapMaxPinchDelta = 18;

  const getDistance = (touchA, touchB) => {
    const distX = touchB.clientX - touchA.clientX;
    const distY = touchB.clientY - touchA.clientY;
    return Math.sqrt(distX * distX + distY * distY);
  };

  const getCenter = (touchA, touchB) => {
    return {
      x: (touchA.clientX + touchB.clientX) / 2,
      y: (touchA.clientY + touchB.clientY) / 2
    };
  };

  return function bindSwipe(element) {
    if (!element || element.__epubSwipeBound) return;
    element.__epubSwipeBound = true;

    let startX = 0;
    let startY = 0;
    let startTime = 0;

    let multiTouchActive = false;
    let pinchStartDistance = 0;
    let multiTouchStartedAt = 0;
    let multiTouchStartCenterX = 0;
    let multiTouchStartCenterY = 0;
    let multiTouchMaxTravel = 0;
    let multiTouchMaxPinchDelta = 0;
    let didPinchResize = false;

    const resetSingleTouch = () => {
      startX = 0;
      startY = 0;
      startTime = 0;
    };

    const resetMultiTouch = () => {
      multiTouchActive = false;
      pinchStartDistance = 0;
      multiTouchStartedAt = 0;
      multiTouchStartCenterX = 0;
      multiTouchStartCenterY = 0;
      multiTouchMaxTravel = 0;
      multiTouchMaxPinchDelta = 0;
      didPinchResize = false;
    };

    const onTouchStart = (event) => {
      const touches = event.touches;
      if (!touches || !touches.length) return;

      if (touches.length >= 2) {
        const touchA = touches[0];
        const touchB = touches[1];
        const center = getCenter(touchA, touchB);

        multiTouchActive = true;
        multiTouchStartedAt = Date.now();
        pinchStartDistance = getDistance(touchA, touchB);
        multiTouchStartCenterX = center.x;
        multiTouchStartCenterY = center.y;
        multiTouchMaxTravel = 0;
        multiTouchMaxPinchDelta = 0;
        didPinchResize = false;
        resetSingleTouch();
        return;
      }

      if (multiTouchActive) return;

      const touch = touches[0];
      startX = touch.clientX;
      startY = touch.clientY;
      startTime = Date.now();
    };

    const onTouchMove = (event) => {
      if (!multiTouchActive) return;

      const touches = event.touches;
      if (!touches || touches.length < 2) return;

      if (event.cancelable) {
        event.preventDefault();
      }

      const touchA = touches[0];
      const touchB = touches[1];
      const center = getCenter(touchA, touchB);
      const currentDistance = getDistance(touchA, touchB);

      const travelX = center.x - multiTouchStartCenterX;
      const travelY = center.y - multiTouchStartCenterY;
      const travel = Math.sqrt(travelX * travelX + travelY * travelY);
      if (travel > multiTouchMaxTravel) {
        multiTouchMaxTravel = travel;
      }

      const pinchDelta = currentDistance - pinchStartDistance;
      const absPinchDelta = Math.abs(pinchDelta);
      if (absPinchDelta > multiTouchMaxPinchDelta) {
        multiTouchMaxPinchDelta = absPinchDelta;
      }

      if (absPinchDelta >= pinchThreshold) {
        const steps = Math.floor(absPinchDelta / pinchThreshold);
        const direction = pinchDelta > 0 ? 1 : -1;

        onChangeFontSize?.(direction * steps);
        didPinchResize = true;
        pinchStartDistance = currentDistance;
      }
    };

    const onTouchEnd = (event) => {
      if (multiTouchActive) {
        if (event.touches && event.touches.length > 0) return;

        const elapsed = Date.now() - multiTouchStartedAt;
        if (
          !didPinchResize &&
          elapsed <= twoFingerTapMaxDuration &&
          multiTouchMaxTravel <= twoFingerTapMaxTravel &&
          multiTouchMaxPinchDelta <= twoFingerTapMaxPinchDelta
        ) {
          onCycleTheme?.();
        }

        resetMultiTouch();
        return;
      }

      const touch = event.changedTouches && event.changedTouches[0];
      if (!touch || !startTime) return;

      const distX = touch.clientX - startX;
      const distY = touch.clientY - startY;
      const elapsedTime = Date.now() - startTime;

      if (elapsedTime <= timeLimit) {
        if (
          distX < 0 &&
          Math.abs(distX) >= swipeThresholdNext &&
          Math.abs(distX) > 2 * Math.abs(distY)
        ) {
          onNext?.();
        } else if (
          distX > 0 &&
          Math.abs(distX) >= swipeThresholdPrev &&
          Math.abs(distX) > 4 * Math.abs(distY)
        ) {
          onPrev?.();
        }
      }

      resetSingleTouch();
    };

    element.addEventListener("touchstart", onTouchStart, { passive: true });
    element.addEventListener("touchmove", onTouchMove, { passive: false });
    element.addEventListener("touchend", onTouchEnd, { passive: true });
    element.addEventListener("touchcancel", () => {
      resetSingleTouch();
      resetMultiTouch();
    });
  };
}

export function bindDoubleTapToggle({
  element,
  onToggle,
  isInteractiveTarget,
  setLastGlobalTouchTime,
  getLastGlobalTouchTime
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

  const clearSelection = () => {
    const selection =
      ownerWindow?.getSelection?.() ||
      ownerDocument?.getSelection?.() ||
      window.getSelection?.() ||
      null;

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
