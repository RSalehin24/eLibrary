function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 5.25v13.5M5.25 12h13.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ExportToggleIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 3v12m0 0l-4-4m4 4l4-4M4 19h16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ManualBooksToolbarActions({
  composerOpen,
  exportRowExpanded,
  onToggleExportRow,
  onToggleComposer
}) {
  return (
    <div className="manual-books-toolbar-actions">
      <div className="toolbar-action-panel toolbar-action-panel-compact is-bare">
        <button
          type="button"
          className={`toolbar-icon-button is-icon-only${
            exportRowExpanded ? " is-active" : ""
          }`}
          onClick={onToggleExportRow}
          aria-expanded={exportRowExpanded}
          title="Export options"
          aria-label="Export options"
        >
          <span className="toolbar-icon-button-art">
            <ExportToggleIcon />
          </span>
        </button>
      </div>

      <div className="toolbar-action-panel toolbar-action-panel-compact is-bare">
        <button
          type="button"
          className={`toolbar-icon-button toolbar-icon-button-accent is-icon-only${
            composerOpen ? " is-active" : ""
          }`}
          onClick={onToggleComposer}
          aria-expanded={composerOpen}
          aria-controls="manual-book-composer"
          title={composerOpen ? "Close add book form" : "Add manual book"}
          aria-label={composerOpen ? "Close add book form" : "Add manual book"}
        >
          <span className="toolbar-icon-button-art">
            <PlusIcon />
          </span>
        </button>
      </div>
    </div>
  );
}
