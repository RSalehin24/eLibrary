export function query(selector, root = document) {
  return root.querySelector(selector);
}

export function queryAll(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

export function showElement(element) {
  if (!element) return;
  element.style.display = "";
}

export function showElementFlex(element) {
  if (!element) return;
  element.style.display = "flex";
}

export function hideElement(element) {
  if (!element) return;
  element.style.display = "none";
}

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export function addClass(element, className) {
  if (!element) return;
  element.classList.add(className);
}

export function removeClass(element, className) {
  if (!element) return;
  element.classList.remove(className);
}

export function hasClass(element, className) {
  return !!(element && element.classList.contains(className));
}

export function toggleClass(element, className, force) {
  if (!element) return;
  element.classList.toggle(className, force);
}

export function delegateEvent(root, eventName, selector, handler, options) {
  if (!root) return () => {};

  const listener = (event) => {
    const target = event.target instanceof Element ? event.target.closest(selector) : null;
    if (!target || !root.contains(target)) return;
    handler(event, target);
  };

  root.addEventListener(eventName, listener, options);

  return () => {
    root.removeEventListener(eventName, listener, options);
  };
}
