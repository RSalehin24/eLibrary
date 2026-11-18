function ToastIcon({ type }) {
  if (type === "success") {
    return (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M4.5 10.5 8 14l7.5-8.5" />
      </svg>
    );
  }

  if (type === "error") {
    return (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="m6 6 8 8" />
        <path d="m14 6-8 8" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10 5.75v4.75" />
      <path d="M10 14.25h.01" />
      <circle cx="10" cy="10" r="7.25" />
    </svg>
  );
}

export default function ToastViewport({ toasts, onDismiss }) {
  return (
    <div className="toast-viewport" aria-live="polite" aria-atomic="true">
      {toasts.map((toast) => (
        <article
          key={toast.id}
          className={`toast toast-${toast.type}`}
          role={toast.type === "error" ? "alert" : "status"}
          data-testid={`notification-toast-${toast.id}`}
        >
          <div className="toast-accent" aria-hidden="true" />
          <div className="toast-icon-shell" aria-hidden="true">
            <ToastIcon type={toast.type} />
          </div>
          <div className="toast-copy">
            <strong>{toast.title}</strong>
            {toast.description ? <p>{toast.description}</p> : null}
          </div>
          <button
            type="button"
            className="toast-dismiss"
            onClick={() => onDismiss(toast.id)}
            aria-label="Dismiss notification"
          >
            ×
          </button>
        </article>
      ))}
    </div>
  );
}
