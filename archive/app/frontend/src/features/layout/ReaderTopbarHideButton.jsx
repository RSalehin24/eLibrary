export function ReaderTopbarHideButton({ onClick }) {
  return (
    <button
      type="button"
      className="reader-topbar-floating-hide"
      onClick={onClick}
      aria-label="Hide reader header"
      title="Hide reader header"
      data-testid="reader-hide-header-button"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3.25" y="4" width="17.5" height="15.5" rx="2.3" ry="2.3" />
        <path d="M3.5 9h17" />
        <path d="M12 16.5v-4M10.5 14l1.5-1.5 1.5 1.5" />
      </svg>
    </button>
  );
}
