import { useEffect, useRef } from "react";
import AsyncButton from "./AsyncButton";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export default function ConfirmationDialog({
  open,
  title,
  body,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  loading = false,
}) {
  const dialogRef = useRef(null);
  const previouslyFocusedRef = useRef(null);

  useEffect(() => {
    if (!open) {
      return undefined;
    }

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
        if (!loading) {
          event.preventDefault();
          onCancel?.();
        }
        return;
      }
      if (event.key !== "Tab") {
        return;
      }
      const nodes = dialogRef.current?.querySelectorAll(FOCUSABLE_SELECTOR);
      if (!nodes || nodes.length === 0) {
        return;
      }
      const items = Array.from(nodes).filter(
        (node) => node instanceof HTMLElement && !node.hasAttribute("disabled"),
      );
      if (items.length === 0) {
        return;
      }
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
  }, [open, loading, onCancel]);

  if (!open) {
    return null;
  }

  function handleBackdropMouseDown(event) {
    if (event.target === event.currentTarget && !loading) {
      onCancel?.();
    }
  }

  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={handleBackdropMouseDown}
    >
      <section
        ref={dialogRef}
        className="dialog-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirmation-dialog-title"
      >
        <div className="dialog-header">
          <div>
            <h2 id="confirmation-dialog-title">{title}</h2>
          </div>
        </div>
        <p className="muted-copy">{body}</p>
        <div className="dialog-actions dialog-actions-end">
          <button
            type="button"
            className="ghost-button"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel}
          </button>
          <AsyncButton
            className="primary-button danger-button"
            onClick={onConfirm}
            loading={loading}
            loadingLabel="Deleting..."
          >
            {confirmLabel}
          </AsyncButton>
        </div>
      </section>
    </div>
  );
}
