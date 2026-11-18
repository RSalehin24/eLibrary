export default function BookDetailSkeleton() {
  return (
    <div className="book-detail-page page-stack book-detail-page-loading" aria-hidden="true">
      <section className="detail-card book-hero">
        <div className="book-hero-cover">
          <div className="book-cover-placeholder book-cover-large book-hero-placeholder book-hero-cover-skeleton">
            <span className="book-cover-kicker skeleton-pill skeleton-pill-sm" />
            <div className="book-card-cover-copy-skeleton">
              <span className="skeleton-line skeleton-line-hero-cover-title" />
              <span className="skeleton-line skeleton-line-hero-cover-author" />
            </div>
          </div>
        </div>
        <div className="book-hero-copy">
          <div className="section-title-block skeleton-heading-block">
            <span className="skeleton-line skeleton-line-eyebrow" />
            <span className="skeleton-line skeleton-line-hero-title" />
          </div>
          <div className="detail-lead-skeleton">
            <span className="skeleton-line skeleton-line-hero-lead" />
          </div>
          <div className="detail-statuses">
            <span className="status-pill skeleton-pill" />
            <span className="status-pill skeleton-pill" />
          </div>
          <div className="book-meta-stack">
            <div className="detail-meta-row skeleton-meta-row">
              <span className="skeleton-line skeleton-line-chip-label" />
              <span className="skeleton-line skeleton-line-hero-meta" />
            </div>
            <div className="detail-meta-row skeleton-meta-row">
              <span className="skeleton-line skeleton-line-chip-label" />
              <span className="skeleton-line skeleton-line-hero-meta-wide" />
            </div>
            <div className="detail-meta-row skeleton-meta-row">
              <span className="skeleton-line skeleton-line-chip-label" />
              <span className="skeleton-line skeleton-line-hero-meta" />
            </div>
          </div>
          <div className="book-hero-actions">
            <span className="primary-button skeleton-button skeleton-button-wide" />
            <span className="ghost-button skeleton-button skeleton-button-wide" />
            <span className="ghost-button skeleton-button skeleton-button-wide" />
          </div>
          <div className="book-status-note book-status-note-processing skeleton-note-card">
            <div className="book-status-note-head">
              <span className="skeleton-line skeleton-line-chip-label" />
            </div>
            <span className="skeleton-line skeleton-line-note-title" />
            <div className="skeleton-paragraph">
              <span className="skeleton-line skeleton-line-note-body" />
              <span className="skeleton-line skeleton-line-note-body-short" />
            </div>
          </div>
        </div>
      </section>

      <section className="detail-card">
        <div className="section-title-block skeleton-heading-block">
          <span className="skeleton-line skeleton-line-eyebrow" />
          <span className="skeleton-line skeleton-line-section-title" />
        </div>
        <div className="source-record-list">
          <article className="source-record-card source-record-card-skeleton">
            <div className="source-record-copy">
              <span className="skeleton-line skeleton-line-chip-label" />
              <span className="skeleton-line skeleton-line-source-title" />
              <span className="skeleton-line skeleton-line-source-url" />
            </div>
            <span className="ghost-button skeleton-button skeleton-button-sm" />
          </article>
          <article className="source-record-card source-record-card-skeleton">
            <div className="source-record-copy">
              <span className="skeleton-line skeleton-line-chip-label" />
              <span className="skeleton-line skeleton-line-source-title" />
              <span className="skeleton-line skeleton-line-source-url-short" />
            </div>
            <span className="ghost-button skeleton-button skeleton-button-sm" />
          </article>
        </div>
      </section>

      <section className="detail-card">
        <div className="section-title-block skeleton-heading-block">
          <span className="skeleton-line skeleton-line-eyebrow" />
          <span className="skeleton-line skeleton-line-section-title" />
        </div>
        <div className="metadata-list">
          <div className="metadata-row skeleton-meta-row">
            <span className="skeleton-line skeleton-line-chip-label" />
            <span className="skeleton-line skeleton-line-metadata-value" />
          </div>
          <div className="metadata-row skeleton-meta-row">
            <span className="skeleton-line skeleton-line-chip-label" />
            <span className="skeleton-line skeleton-line-metadata-value-short" />
          </div>
          <div className="metadata-row skeleton-meta-row">
            <span className="skeleton-line skeleton-line-chip-label" />
            <span className="skeleton-line skeleton-line-metadata-value" />
          </div>
        </div>
      </section>

      <section className="book-detail-grid">
        <section className="detail-card">
          <div className="section-title-block skeleton-heading-block">
            <span className="skeleton-line skeleton-line-eyebrow" />
            <span className="skeleton-line skeleton-line-section-title" />
          </div>
          <div className="reader-stats-grid">
            <article className="book-detail-chip book-detail-chip-skeleton">
              <span className="skeleton-line skeleton-line-chip-label" />
              <span className="skeleton-line skeleton-line-chip-value" />
            </article>
            <article className="book-detail-chip book-detail-chip-skeleton">
              <span className="skeleton-line skeleton-line-chip-label" />
              <span className="skeleton-line skeleton-line-chip-value" />
            </article>
            <article className="book-detail-chip book-detail-chip-skeleton">
              <span className="skeleton-line skeleton-line-chip-label" />
              <span className="skeleton-line skeleton-line-chip-value-short" />
            </article>
          </div>
        </section>

        <section className="detail-card">
          <div className="section-title-block skeleton-heading-block">
            <span className="skeleton-line skeleton-line-eyebrow" />
            <span className="skeleton-line skeleton-line-section-title" />
          </div>
          <div className="queue-list">
            <article className="queue-card queue-card-skeleton">
              <span className="skeleton-line skeleton-line-queue-title" />
              <span className="skeleton-line skeleton-line-queue-meta" />
              <div className="inline-pills">
                <span className="ghost-button skeleton-button skeleton-button-sm" />
              </div>
            </article>
            <article className="queue-card queue-card-skeleton">
              <span className="skeleton-line skeleton-line-queue-title" />
              <span className="skeleton-line skeleton-line-queue-meta-short" />
              <div className="inline-pills">
                <span className="ghost-button skeleton-button skeleton-button-sm" />
              </div>
            </article>
          </div>
        </section>
      </section>
    </div>
  );
}
