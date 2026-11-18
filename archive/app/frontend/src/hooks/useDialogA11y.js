import { useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

// Applies focus trap, body scroll lock, focus restoration, and Escape handling
// to a modal/dialog element. Returns a ref to attach to the dialog root.
export function useDialogA11y(open, { onClose, locked = false } = {}) {
  const dialogRef = useRef(null);
  const previouslyFocusedRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    previouslyFocusedRef.current =
      typeof document !== "undefined" ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const focusables = dialogRef.current?.querySelectorAll(FOCUSABLE_SELECTOR);
    const first = focusables?.[0];
    if (first instanceof HTMLElement) {
      first.focus();
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        if (!locked) {
          event.preventDefault();
          onClose?.();
        }
        return;
      }
      if (event.key !== "Tab") return;
      const nodes = dialogRef.current?.querySelectorAll(FOCUSABLE_SELECTOR);
      if (!nodes || nodes.length === 0) return;
      const items = Array.from(nodes).filter(
        (node) => node instanceof HTMLElement && !node.hasAttribute("disabled"),
      );
      if (items.length === 0) return;
      const firstNode = items[0];
      const lastNode = items[items.length - 1];
      if (event.shiftKey && document.activeElement === firstNode) {
        event.preventDefault();
        lastNode.focus();
      } else if (!event.shiftKey && document.activeElement === lastNode) {
        event.preventDefault();
        firstNode.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      const previous = previouslyFocusedRef.current;
      if (previous instanceof HTMLElement) {
        try {
          previous.focus();
        } catch {
          // ignore
        }
      }
    };
  }, [open, locked, onClose]);

  return dialogRef;
}
