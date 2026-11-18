export function ProcessingCountSkeleton() {
  return (
    <span
      className="processing-card-count processing-card-count-skeleton"
      aria-hidden="true"
    />
  );
}

export function ProcessingValueSkeleton() {
  return <span className="processing-value-skeleton" aria-hidden="true" />;
}

export default function ProcessingCardSkeleton({ label = "Loading" }) {
  return (
    <div
      className="processing-inline-loader processing-inline-skeleton"
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <span className="sr-only">{label}</span>
      <div className="processing-skeleton" aria-hidden="true">
        <div className="processing-skeleton-summary">
          {Array.from({ length: 4 }, (_, index) => (
            <article key={`stat-${index}`} className="processing-skeleton-stat">
              <span className="skeleton-line skeleton-line-sm" />
              <ProcessingValueSkeleton />
            </article>
          ))}
        </div>
        <div className="processing-skeleton-table">
          {Array.from({ length: 5 }, (_, rowIndex) => (
            <div key={`row-${rowIndex}`} className="processing-skeleton-row">
              <span className="skeleton-line skeleton-line-xl" />
              <span className="skeleton-line skeleton-line-sm" />
              <span className="skeleton-line skeleton-line-sm" />
              <span className="skeleton-line skeleton-line-sm" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
