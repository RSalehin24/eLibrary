function CsvIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M7.25 4.75h7.72l4.03 4.03v9.97A2.25 2.25 0 0 1 16.75 21h-9.5A2.25 2.25 0 0 1 5 18.75v-11.5A2.25 2.25 0 0 1 7.25 5Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M14.75 4.75v4h4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M8 11.5h8M8 15h8M8 18.5h5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function PdfIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M7.25 4.75h7.72l4.03 4.03v9.97A2.25 2.25 0 0 1 16.75 21h-9.5A2.25 2.25 0 0 1 5 18.75v-11.5A2.25 2.25 0 0 1 7.25 5Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M14.75 4.75v4h4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path
        d="M8.1 16.7v-4.8h1.56c.92 0 1.54.56 1.54 1.43 0 .9-.62 1.47-1.54 1.47H9.4v1.9M13 16.7v-4.8h1.44c1.44 0 2.33.91 2.33 2.4 0 1.48-.89 2.4-2.33 2.4H13ZM9.4 13.75h.26c.36 0 .57-.19.57-.49 0-.28-.21-.47-.57-.47H9.4ZM14 15.63h.35c.85 0 1.38-.47 1.38-1.33 0-.88-.53-1.35-1.38-1.35H14Z"
        fill="currentColor"
      />
    </svg>
  );
}

const exportItems = [
  { value: "csv", label: "CSV export", shortLabel: "CSV", icon: <CsvIcon /> },
  { value: "pdf", label: "PDF export", shortLabel: "PDF", icon: <PdfIcon /> }
];

export default function ExportActions({
  loading = "",
  onExport,
  bare = false,
  disabled = false,
  ariaLabel = "Export books"
}) {
  return (
    <div className={`toolbar-action-panel${bare ? " is-bare" : ""}`}>
      <div className="toolbar-action-cluster" role="group" aria-label={ariaLabel}>
        {exportItems.map((item) => {
          const isLoading = loading === item.value;
          return (
            <button
              key={item.value}
              type="button"
              className={`toolbar-icon-button export-action-button${isLoading ? " is-loading" : ""}`}
              onClick={() => {
                if (!disabled && loading === "") {
                  onExport(item.value);
                }
              }}
              disabled={disabled || loading !== ""}
              aria-label={isLoading ? `${item.label} is generating` : item.label}
              title={item.label}
            >
              <span className="toolbar-icon-button-art">
                {isLoading ? <span className="loading-spinner" aria-hidden="true" /> : item.icon}
              </span>
              <span className="toolbar-icon-button-text">{item.shortLabel}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
