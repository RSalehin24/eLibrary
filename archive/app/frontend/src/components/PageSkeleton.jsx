function SkeletonTable({ columns = 6, rows = 5 }) {
  return (
    <div
      className="page-loader-table"
      style={{ "--page-loader-columns": columns }}
    >
      <div className="page-loader-table-row page-loader-table-row-head">
        {Array.from({ length: columns }, (_, index) => (
          <span
            key={`head-${index}`}
            className={`skeleton-line page-loader-table-cell${
              index === 0
                ? " page-loader-table-cell-wide"
                : index === columns - 1
                  ? " page-loader-table-cell-short"
                  : ""
            }`}
          />
        ))}
      </div>
      {Array.from({ length: rows }, (_, rowIndex) => (
        <div key={`row-${rowIndex}`} className="page-loader-table-row">
          {Array.from({ length: columns }, (_, cellIndex) => (
            <span
              key={`row-${rowIndex}-cell-${cellIndex}`}
              className={`skeleton-line page-loader-table-cell${
                cellIndex === 0
                  ? " page-loader-table-cell-wide"
                  : cellIndex === columns - 1
                    ? " page-loader-table-cell-short"
                    : ""
              }`}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function SkeletonField({ short = false, multiline = false }) {
  return (
    <div className="page-loader-field">
      <span className="skeleton-line skeleton-line-sm" />
      <span
        className={`skeleton-panel ${
          multiline
            ? "page-loader-input-area"
            : short
              ? "page-loader-input-short"
              : "page-loader-input"
        }`}
      />
    </div>
  );
}

function SkeletonActionRow({ count = 2, wide = false }) {
  return (
    <div className="inline-pills page-loader-actions-row">
      {Array.from({ length: count }, (_, index) => (
        <span
          key={`action-${index}`}
          className={`skeleton-button ${wide ? "skeleton-button-wide" : "skeleton-button-sm"}`}
        />
      ))}
    </div>
  );
}

function renderTableSkeleton() {
  return (
    <div className="page-loader-shell page-loader-shell-table">
      <section className="detail-card page-loader-surface page-loader-table-card">
        <div className="page-loader-table-shell">
          <SkeletonTable columns={6} rows={6} />
        </div>
      </section>
    </div>
  );
}

function renderManagementSkeleton() {
  return (
    <div className="page-stack access-page page-loader-shell page-loader-shell-management">
      <section className="detail-card admin-hero-card page-loader-surface page-loader-management-hero">
        <div className="page-loader-copy-block">
          <span className="skeleton-line skeleton-line-eyebrow" />
          <span className="skeleton-line page-loader-line-page-title" />
          <span className="skeleton-line skeleton-line-xl" />
        </div>
        <SkeletonActionRow count={2} wide />
      </section>

      <section className="detail-card page-loader-surface">
        <div className="panel-header">
          <span className="skeleton-line page-loader-line-section-title" />
          <span className="skeleton-button skeleton-button-sm" />
        </div>
        <div className="page-loader-form-grid">
          <SkeletonField />
          <SkeletonField />
          <SkeletonField />
          <SkeletonField short />
        </div>
        <div className="page-loader-chip-grid">
          {Array.from({ length: 6 }, (_, index) => (
            <span
              key={`management-chip-${index}`}
              className="skeleton-panel page-loader-chip-card"
            />
          ))}
        </div>
      </section>

      <section className="detail-card page-loader-surface page-loader-table-card">
        <div className="panel-header">
          <span className="skeleton-line page-loader-line-section-title" />
          <span className="skeleton-pill skeleton-pill-xs" />
        </div>
        <div className="page-loader-toolbar-row page-loader-toolbar-row-table">
          <span className="skeleton-panel page-loader-input page-loader-search-input" />
          <span className="skeleton-button skeleton-button-sm" />
          <span className="skeleton-button skeleton-button-sm" />
          <span className="skeleton-pill skeleton-pill-xs" />
        </div>
        <div className="page-loader-table-shell">
          <SkeletonTable columns={6} rows={5} />
        </div>
      </section>
    </div>
  );
}

function renderProfileSkeleton() {
  return (
    <div className="page-stack page-loader-shell page-loader-shell-profile">
      <section className="detail-card profile-shell page-loader-surface">
        <div className="panel-header profile-header-bar">
          <span className="skeleton-line page-loader-line-page-title" />
          <span className="skeleton-button skeleton-button-sm" />
        </div>

        <div className="page-loader-profile-summary">
          <span className="skeleton-block page-loader-avatar" />
          <div className="page-loader-copy-block">
            <span className="skeleton-line page-loader-line-profile-name" />
            <span className="skeleton-line skeleton-line-lg" />
            <div className="detail-statuses">
              <span className="status-pill skeleton-pill skeleton-pill-sm" />
              <span className="status-pill skeleton-pill skeleton-pill-sm" />
            </div>
          </div>
        </div>

        <div className="page-loader-detail-grid">
          <SkeletonField />
          <SkeletonField />
          <SkeletonField short />
          <SkeletonField short />
        </div>

        <div className="page-loader-profile-panels">
          <div className="skeleton-panel page-loader-inline-card page-loader-inline-card-lg" />
          <div className="skeleton-panel page-loader-inline-card" />
        </div>
      </section>
    </div>
  );
}

function renderAuthSkeleton() {
  return (
    <div className="login-shell page-loader-shell page-loader-shell-auth">
      <section className="detail-card login-card page-loader-surface page-loader-auth-card">
        <div className="page-loader-copy-block">
          <span className="skeleton-line skeleton-line-eyebrow" />
          <span className="skeleton-line page-loader-line-auth-title" />
          <span className="skeleton-line skeleton-line-lg" />
        </div>
        <div className="page-loader-form-stack">
          <SkeletonField />
          <SkeletonField />
        </div>
        <SkeletonActionRow count={2} wide />
      </section>
    </div>
  );
}

function renderReaderSkeleton() {
  return (
    <div className="page-loader-shell page-loader-shell-reader">
      <div className="page-loader-reader-frame">
        <div className="page-loader-reader-nav">
          <span className="skeleton-button skeleton-button-sm" />
          <span className="skeleton-button skeleton-button-sm" />
          <span className="skeleton-button skeleton-button-sm" />
        </div>
        <div className="page-loader-reader-stage">
          <span className="skeleton-panel page-loader-reader-edge" />
          <div className="skeleton-panel page-loader-reader-page">
            <div className="page-loader-reader-page-copy">
              <span className="skeleton-line page-loader-line-page-title" />
              <span className="skeleton-line skeleton-line-xl" />
              <span className="skeleton-line skeleton-line-xl" />
              <span className="skeleton-line skeleton-line-lg" />
            </div>
          </div>
          <span className="skeleton-panel page-loader-reader-edge" />
        </div>
      </div>
    </div>
  );
}

function renderCardSkeleton() {
  return (
    <div className="page-loader-shell page-loader-shell-card">
      <div className="page-loader-card page-loader-surface">
        <div className="page-loader-copy-block">
          <span className="skeleton-line page-loader-line-section-title" />
          <span className="skeleton-line skeleton-line-lg" />
        </div>
        <div className="page-loader-form-stack">
          <SkeletonField multiline />
          <SkeletonField />
        </div>
        <SkeletonActionRow count={2} />
      </div>
    </div>
  );
}

function renderGenericSkeleton() {
  return (
    <div className="page-stack page-loader-shell page-loader-shell-generic">
      <section className="detail-card page-loader-surface">
        <div className="page-loader-copy-block">
          <span className="skeleton-line page-loader-line-page-title" />
          <span className="skeleton-line skeleton-line-xl" />
        </div>
      </section>
      <section className="detail-card page-loader-surface page-loader-table-card">
        <div className="page-loader-table-shell">
          <SkeletonTable columns={5} rows={4} />
        </div>
      </section>
    </div>
  );
}

export default function PageSkeleton({ variant = "table" }) {
  if (variant === "management") {
    return renderManagementSkeleton();
  }
  if (variant === "profile") {
    return renderProfileSkeleton();
  }
  if (variant === "auth") {
    return renderAuthSkeleton();
  }
  if (variant === "reader") {
    return renderReaderSkeleton();
  }
  if (variant === "card") {
    return renderCardSkeleton();
  }
  if (variant === "table") {
    return renderTableSkeleton();
  }
  return renderGenericSkeleton();
}
