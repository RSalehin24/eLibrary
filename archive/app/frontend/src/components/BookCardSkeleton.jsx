export default function BookCardSkeleton({ testId = undefined }) {
  return (
    <article
      className="book-card book-card-skeleton"
      aria-hidden="true"
      data-testid={testId}
    >
      <div className="book-card-art">
        <div className="book-cover-placeholder book-card-cover book-card-cover-skeleton">
          <span className="book-cover-kicker skeleton-pill skeleton-pill-sm" />
          <div className="book-card-cover-copy-skeleton">
            <span className="skeleton-line skeleton-line-cover-title" />
            <span className="skeleton-line skeleton-line-cover-author" />
          </div>
        </div>
      </div>

      <div className="book-card-body">
        <div className="book-card-topline">
          <span className="skeleton-line skeleton-line-card-id" />
        </div>
        <div className="book-card-heading">
          <span className="skeleton-line skeleton-line-card-title" />
          <div className="book-card-contributors">
            <span className="skeleton-line skeleton-line-card-contributor" />
            <div className="book-meta-secondary book-meta-secondary-skeleton">
              <span className="book-meta-role skeleton-pill skeleton-pill-xs" />
              <span className="skeleton-line skeleton-line-card-secondary" />
            </div>
          </div>
        </div>
        <div className="book-card-details">
          <div className="book-detail-chip book-detail-chip-skeleton">
            <span className="skeleton-line skeleton-line-chip-label" />
            <span className="skeleton-line skeleton-line-chip-value" />
          </div>
          <div className="book-detail-chip book-detail-chip-skeleton">
            <span className="skeleton-line skeleton-line-chip-label" />
            <span className="skeleton-line skeleton-line-chip-value" />
          </div>
        </div>
        <div className="book-card-footer">
          <span className="skeleton-line skeleton-line-timestamp" />
          <span className="primary-button book-card-action skeleton-button" />
        </div>
      </div>
    </article>
  );
}
