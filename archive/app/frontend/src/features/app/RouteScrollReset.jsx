import { useEffect, useLayoutEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

const SCROLL_PRESERVED_PATHS = new Set(["/reader"]);

function resetDocumentScroll() {
  const scrollTargets = [
    document.scrollingElement,
    document.documentElement,
    document.body,
  ].filter(Boolean);

  for (const target of scrollTargets) {
    target.scrollLeft = 0;
    target.scrollTop = 0;
  }

  window.scrollTo({
    left: 0,
    top: 0,
    behavior: "auto",
  });
}

export default function RouteScrollReset() {
  const location = useLocation();
  const previousPathnameRef = useRef(null);

  useEffect(() => {
    if (!("scrollRestoration" in window.history)) {
      return undefined;
    }

    const previousScrollRestoration = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";
    return () => {
      window.history.scrollRestoration = previousScrollRestoration;
    };
  }, []);

  useLayoutEffect(() => {
    if (previousPathnameRef.current === location.pathname) {
      return undefined;
    }

    previousPathnameRef.current = location.pathname;

    if (SCROLL_PRESERVED_PATHS.has(location.pathname) || location.hash) {
      return undefined;
    }

    resetDocumentScroll();
    const animationFrame = window.requestAnimationFrame(resetDocumentScroll);

    return () => {
      window.cancelAnimationFrame(animationFrame);
    };
  }, [location.hash, location.pathname]);

  return null;
}
