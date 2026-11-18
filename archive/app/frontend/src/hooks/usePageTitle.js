import { useEffect } from "react";

const BASE_TITLE = "eLibrary";

// Sets the document title to `${segment} · eLibrary` (or just `eLibrary` if
// segment is falsy). Restores the previous title on unmount.
export function usePageTitle(segment) {
  useEffect(() => {
    if (typeof document === "undefined") return undefined;
    const previous = document.title;
    document.title = segment ? `${segment} · ${BASE_TITLE}` : BASE_TITLE;
    return () => {
      document.title = previous;
    };
  }, [segment]);
}
