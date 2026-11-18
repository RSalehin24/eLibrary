import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

const SCROLL_PAGES = new Set(["/home", "/my-books", "/notes"]);

export default function ScrollToTopButton() {
  const { pathname } = useLocation();
  const [visible, setVisible] = useState(false);

  const isEligible = SCROLL_PAGES.has(pathname);

  useEffect(() => {
    if (!isEligible) {
      setVisible(false);
      return;
    }

    function check() {
      setVisible(window.scrollY > window.innerHeight);
    }

    window.addEventListener("scroll", check, { passive: true });
    check();
    return () => window.removeEventListener("scroll", check);
  }, [isEligible]);

  if (!visible) {
    return null;
  }

  return (
    <button
      type="button"
      className="scroll-to-top-button"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      aria-label="Back to top"
      title="Back to top"
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M18 15l-6-6-6 6" />
      </svg>
    </button>
  );
}
