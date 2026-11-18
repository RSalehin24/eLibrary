export default function ReaderUnavailable({
  error,
  navHidden,
  navigate,
  targetBookPath,
  toggleAppNav,
}) {
  return (
    <section className="page-state reader-page-state">
      <h2>Reader unavailable</h2>
      <p>{error}</p>
      <div className="reader-toolbar">
        <button
          type="button"
          className="reader-header-icon"
          onClick={toggleAppNav}
          aria-label={navHidden ? "Show main header" : "Hide main header"}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M3 6.75h18M3 12h18M3 17.25h18" />
          </svg>
        </button>
        <button
          type="button"
          className="reader-header-icon"
          onClick={() => navigate(targetBookPath)}
          aria-label="Back to book"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M14.5 6.5L8.5 12l6 5.5" />
          </svg>
        </button>
      </div>
    </section>
  );
}
