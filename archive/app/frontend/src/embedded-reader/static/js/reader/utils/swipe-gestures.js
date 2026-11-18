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
