import { ProcessingValueSkeleton } from "../../../components/ProcessingCardSkeleton";
import { useBookProcessing } from "../BookProcessingStore";
import { REQUEST_STATE_LABELS } from "../types";
import { processingStreamStatusMessage } from "./processingPageModel";
export function OverviewStat({ testId, label, value, loading = false }) {
  return (
    <div className="processing-summary-stat" data-testid={testId}>
      <span>{label}</span>
      <strong>{loading ? <ProcessingValueSkeleton /> : value}</strong>
    </div>
  );
}
export function ProcessingStatusSkeleton({
  lines = 1,
  variant = "automation",
}) {
  return (
    <span
      className={`processing-status-skeleton processing-status-skeleton--${variant}`}
      aria-hidden="true"
    >
      <span className="processing-status-line-skeleton processing-status-line-skeleton--wide" />
      {lines > 1 ? (
        <span className="processing-status-line-skeleton processing-status-line-skeleton--short" />
      ) : null}
    </span>
  );
}
export function PlayIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M6.5 4.5v11l8.75-5.5-8.75-5.5Z" />
    </svg>
  );
}
export function PauseIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M6.25 4.75h2.75v10.5H6.25zM11 4.75h2.75v10.5H11z" />
    </svg>
  );
}
export function StopIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M5.75 5.75h8.5v8.5h-8.5z" />
    </svg>
  );
}
export function IconOnlyActionButton({
  testId,
  label,
  icon,
  state = "idle",
  disabled = false,
  onClick,
  className = "",
}) {
  const visualStateClass =
    state === "pausing"
      ? " is-pending"
      : state === "paused"
        ? " is-paused"
        : state === "running" || state === "syncing"
          ? " is-running"
          : "";
  return (
    <button
      type="button"
      className={`toolbar-icon-button toolbar-icon-button-accent is-icon-only processing-icon-button${visualStateClass}${className ? ` ${className}` : ""}`}
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      data-testid={testId}
      data-state={state}
    >
      <span className="toolbar-icon-button-art">{icon}</span>
      <span className="toolbar-icon-button-text">{label}</span>
    </button>
  );
}
export function IconOnlyActionSkeleton({ testId, label, className = "" }) {
  return (
    <button
      type="button"
      className={`toolbar-icon-button toolbar-icon-button-accent is-icon-only processing-icon-button processing-skeleton-control${className ? ` ${className}` : ""}`}
      aria-hidden="true"
      tabIndex={-1}
      data-testid={testId}
    >
      <span className="toolbar-icon-button-art" />
      <span className="toolbar-icon-button-text">{label}</span>
    </button>
  );
}
export function ButtonSkeleton({ testId, label, className = "" }) {
  return (
    <button
      type="button"
      className={`primary-button processing-skeleton-control processing-skeleton-button${className ? ` ${className}` : ""}`}
      aria-hidden="true"
      tabIndex={-1}
      data-testid={testId}
    >
      {label}
    </button>
  );
}
export function SwitchSkeleton({ testId, label = "Off" }) {
  return (
    <label
      className="processing-switch processing-switch-skeleton"
      aria-hidden="true"
      data-testid={testId}
    >
      <input type="checkbox" checked={false} readOnly tabIndex={-1} />
      <span className="processing-switch-track processing-skeleton-control">
        <span className="processing-switch-state">{label}</span>
        <span className="processing-switch-thumb processing-skeleton-control" />
      </span>
    </label>
  );
}
export function AutomationFieldSkeleton({
  testId,
  label,
  controlClassName = "",
}) {
  return (
    <label className="processing-automation-field processing-form-field-skeleton">
      <span className="processing-automation-field-label">{label}</span>
      <span
        className={`processing-automation-field-control processing-automation-field-control--skeleton processing-skeleton-control${controlClassName ? ` ${controlClassName}` : ""}`}
        aria-hidden="true"
        data-testid={testId}
      />
    </label>
  );
}
export function PageFrame({ pageId, title, children }) {
  const { streamMode } = useBookProcessing();
  const streamStatusMessage = processingStreamStatusMessage(streamMode);
  return (
    <div className="processing-page page-stack" data-testid={`${pageId}-page`}>
      <section className="detail-card processing-page-header">
        <div className="panel-header">
          <div>
            <h1>{title}</h1>
            {streamStatusMessage ? (
              <p
                className="processing-table-muted"
                data-testid={`${pageId}-stream-status`}
              >
                {streamStatusMessage}
              </p>
            ) : null}
          </div>
        </div>
      </section>
      {children}
    </div>
  );
}
export function OverviewPanel({ pageId, stats, loading = false }) {
  return (
    <section className="detail-card processing-summary-card">
      <div className="processing-summary-bar">
        {stats.map((stat) => (
          <OverviewStat
            key={stat.id}
            testId={`${pageId}-overview-stat-${stat.id}`}
            label={stat.label}
            value={stat.value}
            loading={loading}
          />
        ))}
      </div>
    </section>
  );
}
export function ActiveFilters({
  pageId,
  cardId,
  categoryFilter,
  statusFilter,
}) {
  const labels = [];
  if (categoryFilter) {
    labels.push(categoryFilter);
  }
  if (statusFilter) {
    labels.push(REQUEST_STATE_LABELS[statusFilter] || statusFilter);
  }
  if (!labels.length) {
    return null;
  }
  return (
    <div
      className="processing-active-filters"
      data-testid={`${pageId}-${cardId}-active-filters`}
    >
      {labels.map((label) => (
        <span key={label} className="processing-active-filter-chip">
          {label}
        </span>
      ))}
    </div>
  );
}
export function MultiPageTocBadge({ row }) {
  if (!row?.hasMultiPageToc) {
    return null;
  }
  const fetched = Number(row.fetchedTocPageCount || 0);
  const source = Number(row.sourceTocPageCount || 0);
  const incomplete = source > 0 && fetched < source;
  const label = source > 0 ? `TOC ${fetched}/${source}` : "Multi-page TOC";
  const title = incomplete
    ? `Multi-page table of contents: only ${fetched} of ${source} pages were retrieved (sign-in may be required).`
    : `Multi-page table of contents: ${source} pages.`;
  return (
    <span
      className={`processing-multipage-badge${incomplete ? " is-incomplete" : ""}`}
      title={title}
      data-testid="multipage-toc-badge"
    >
      {label}
    </span>
  );
}
export function ContributorsCell({ row }) {
  const items = [
    {
      label: "Writer",
      value: row.writer,
    },
    {
      label: "Translator",
      value: row.translator,
    },
    {
      label: "Publisher",
      value: row.publisher,
    },
  ].filter((item) => item.value);
  if (!items.length) {
    return <span className="processing-table-muted">-</span>;
  }
  return (
    <div className="processing-contributors-list">
      {items.map((item) => (
        <div key={item.label} className="processing-contributor-entry">
          <span className="processing-contributor-label">{item.label}</span>
          <span>{item.value}</span>
        </div>
      ))}
    </div>
  );
}
