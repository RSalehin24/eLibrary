import { useCallback, useEffect, useRef, useState } from "react";
import BookRouteLink from "../components/BookRouteLink";
import {
  deleteReprocessJob,
  getReprocessJobs,
  getReprocessSummary,
  resumeReprocessJob,
  stopReprocessJob,
} from "../features/processing/api";
import { SearchIcon } from "../components/catalog-toolbar/icons";
import {
  OverviewPanel,
  PageFrame,
} from "../features/processing/processing-pages/processingPagePrimitives";

const POLL_MS = 15_000;
const PAGE_SIZE = 60;
const ACTIVE_STATUSES = new Set(["queued", "processing"]);
const HISTORY_STATUSES = new Set(["succeeded", "failed", "cancelled"]);

const STATUS_LABELS = {
  queued: "Queued",
  processing: "Active",
  succeeded: "Done",
  failed: "Failed",
  cancelled: "Stopped",
};

function useReprocessData() {
  const [jobs, setJobs] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const timerRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const [jobsData, summaryData] = await Promise.all([
        getReprocessJobs(),
        getReprocessSummary(),
      ]);
      setJobs(jobsData);
      setSummary(summaryData);
    } catch {
      // retain previous data on transient errors
    } finally {
      setLoadedOnce(true);
    }
  }, []);

  useEffect(() => {
    load();
    return () => clearTimeout(timerRef.current);
  }, [load]);

  useEffect(() => {
    clearTimeout(timerRef.current);
    if (jobs?.some((j) => ACTIVE_STATUSES.has(j.status))) {
      timerRef.current = setTimeout(load, POLL_MS);
    }
    return () => clearTimeout(timerRef.current);
  }, [jobs, load]);

  const activeJobs = (jobs ?? []).filter((j) => ACTIVE_STATUSES.has(j.status));
  const historyJobs = (jobs ?? []).filter((j) =>
    HISTORY_STATUSES.has(j.status),
  );

  return { activeJobs, historyJobs, summary, loadedOnce, refresh: load };
}

function StatusBadge({ status }) {
  return (
    <span className={`reprocess-badge reprocess-badge--${status}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

function RelTime({ iso }) {
  if (!iso) return <span className="processing-table-muted">—</span>;
  const d = new Date(iso);
  const secs = Math.floor((Date.now() - d.getTime()) / 1000);
  let text;
  if (secs < 60) text = "just now";
  else if (secs < 3600) text = `${Math.floor(secs / 60)}m ago`;
  else if (secs < 86400) text = `${Math.floor(secs / 3600)}h ago`;
  else text = `${Math.floor(secs / 86400)}d ago`;
  return (
    <time dateTime={iso} title={d.toLocaleString()}>
      {text}
    </time>
  );
}

function BookCell({ job }) {
  const title = job.target_book_title || job.submission_input || "—";
  if (job.target_book_slug && !job.target_book_deleted) {
    return (
      <BookRouteLink
        slug={job.target_book_slug}
        className="processing-book-link"
      >
        {title}
      </BookRouteLink>
    );
  }
  return (
    <span className="processing-table-muted">
      {title}
      {job.target_book_deleted && (
        <span className="reprocess-deleted-tag">Deleted</span>
      )}
    </span>
  );
}

function useJobActions(onDone) {
  const [pending, setPending] = useState(new Set());

  const act = useCallback(
    async (actionFn, id) => {
      setPending((p) => new Set([...p, id]));
      try {
        await actionFn();
        onDone?.();
      } finally {
        setPending((p) => {
          const next = new Set(p);
          next.delete(id);
          return next;
        });
      }
    },
    [onDone],
  );

  return { pending, act };
}

function useRowSelection(rows) {
  const [selected, setSelected] = useState(new Set());

  const visibleIds = rows.map((r) => r.id);
  const allSelected =
    visibleIds.length > 0 && visibleIds.every((id) => selected.has(id));

  function toggleAll() {
    if (allSelected) {
      setSelected((s) => {
        const next = new Set(s);
        visibleIds.forEach((id) => next.delete(id));
        return next;
      });
    } else {
      setSelected((s) => new Set([...s, ...visibleIds]));
    }
  }

  function toggleRow(id) {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function clearSelection() {
    setSelected(new Set());
  }

  const selectedCount = visibleIds.filter((id) => selected.has(id)).length;

  return {
    selected,
    allSelected,
    toggleAll,
    toggleRow,
    clearSelection,
    selectedCount,
  };
}

function filterJobs(jobs, q) {
  if (!q.trim()) return jobs;
  const low = q.toLowerCase();
  return jobs.filter(
    (j) =>
      (j.target_book_title || "").toLowerCase().includes(low) ||
      (j.submission_input || "").toLowerCase().includes(low),
  );
}

function useProgressiveRows(rows) {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const sentinelRef = useRef(null);
  const shellRef = useRef(null);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [rows]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    const shell = shellRef.current;
    if (!sentinel || !shell || visibleCount >= rows.length) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setVisibleCount((c) => Math.min(c + PAGE_SIZE, rows.length));
        }
      },
      { root: shell, threshold: 0.1 },
    );
    obs.observe(sentinel);
    return () => obs.disconnect();
  }, [rows, visibleCount]);

  return {
    visibleRows: rows.slice(0, visibleCount),
    hasMore: visibleCount < rows.length,
    sentinelRef,
    shellRef,
  };
}

function ActiveTable({ jobs, onRefresh }) {
  const [q, setQ] = useState("");
  const filtered = filterJobs(jobs, q);
  const { visibleRows, hasMore, sentinelRef, shellRef } =
    useProgressiveRows(filtered);
  const {
    selected,
    allSelected,
    toggleAll,
    toggleRow,
    clearSelection,
    selectedCount,
  } = useRowSelection(visibleRows);
  const { pending, act } = useJobActions(onRefresh);

  async function stopSelected() {
    const ids = [...selected].filter((id) => jobs.some((j) => j.id === id));
    await Promise.all(
      ids.map((id) => act(() => stopReprocessJob(id), id)),
    );
    clearSelection();
  }

  async function deleteSelected() {
    const ids = [...selected].filter((id) =>
      jobs.some((j) => j.id === id && j.status === "queued"),
    );
    await Promise.all(
      ids.map((id) => act(() => deleteReprocessJob(id), id)),
    );
    clearSelection();
  }

  return (
    <section className="detail-card processing-card processing-list-card processing-card-span-full reprocess-jobs-card">
      <div className="processing-card-head processing-card-head--list">
        <div className="processing-card-head-line">
          <div className="processing-card-head-meta">
            <h2>Active</h2>
          </div>
          <div className="processing-card-head-search">
            <label
              className="catalog-search-field processing-search-field"
              aria-label="Search active jobs"
            >
              <span className="catalog-search-icon">
                <SearchIcon />
              </span>
              <input
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search"
                autoComplete="off"
              />
            </label>
          </div>
          <div className="processing-card-head-inline-tools">
            <span
              className="catalog-result-count processing-card-title-count"
              aria-label={`${filtered.length} results`}
            >
              {filtered.length}
            </span>
          </div>
          <div className="processing-card-head-actions">
            <div className="reprocess-actions-bar">
              {selectedCount > 0 && (
                <span className="reprocess-bulk-count">
                  {selectedCount} selected
                </span>
              )}
              <button
                type="button"
                className="ghost-button reprocess-bulk-btn"
                disabled={selectedCount === 0}
                onClick={stopSelected}
              >
                Stop
              </button>
              <button
                type="button"
                className="reprocess-bulk-btn reprocess-bulk-btn--delete"
                disabled={selectedCount === 0}
                onClick={deleteSelected}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="reprocess-empty">
          {q ? "No matching jobs." : "No active reprocessing jobs."}
        </p>
      ) : (
        <div className="processing-table-shell" ref={shellRef}>
          <table className="reprocess-table">
            <thead>
              <tr>
                <th className="reprocess-col-check">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    aria-label="Select all"
                  />
                </th>
                <th>Book</th>
                <th className="reprocess-col-status">Status</th>
                <th className="reprocess-col-number">Retries</th>
                <th className="reprocess-col-time reprocess-hide-sm">
                  Started
                </th>
                <th className="reprocess-col-time">Updated</th>
                <th className="reprocess-col-actions" />
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((job) => (
                <tr
                  key={job.id}
                  className={selected.has(job.id) ? "is-selected" : undefined}
                >
                  <td className="reprocess-col-check">
                    <input
                      type="checkbox"
                      checked={selected.has(job.id)}
                      onChange={() => toggleRow(job.id)}
                      aria-label="Select row"
                    />
                  </td>
                  <td>
                    <BookCell job={job} />
                  </td>
                  <td>
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="reprocess-col-number processing-table-muted">
                    {job.retry_count ?? 0}
                  </td>
                  <td className="reprocess-hide-sm">
                    <RelTime iso={job.started_at} />
                  </td>
                  <td>
                    <RelTime iso={job.updated_at} />
                  </td>
                  <td>
                    <div className="reprocess-row-actions">
                      {(job.status === "processing" ||
                        job.status === "queued") && (
                        <button
                          type="button"
                          className="ghost-button reprocess-action-btn"
                          disabled={pending.has(job.id)}
                          onClick={() =>
                            act(() => stopReprocessJob(job.id), job.id)
                          }
                        >
                          Stop
                        </button>
                      )}
                      {job.status === "queued" && (
                        <button
                          type="button"
                          className="ghost-button reprocess-action-btn reprocess-action-btn--danger"
                          disabled={pending.has(job.id)}
                          onClick={() =>
                            act(() => deleteReprocessJob(job.id), job.id)
                          }
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {hasMore && (
                <tr ref={sentinelRef} aria-hidden="true">
                  <td colSpan={7} className="reprocess-sentinel-cell" />
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function HistoryTable({ jobs, onRefresh }) {
  const [q, setQ] = useState("");
  const filtered = jobs.filter((j) => {
    if (!q.trim()) return true;
    const low = q.toLowerCase();
    return (
      (j.target_book_title || "").toLowerCase().includes(low) ||
      (j.submission_input || "").toLowerCase().includes(low) ||
      (j.last_error || "").toLowerCase().includes(low)
    );
  });
  const { visibleRows, hasMore, sentinelRef, shellRef } =
    useProgressiveRows(filtered);
  const {
    selected,
    allSelected,
    toggleAll,
    toggleRow,
    clearSelection,
    selectedCount,
  } = useRowSelection(visibleRows);
  const { pending, act } = useJobActions(onRefresh);

  async function resumeSelected() {
    const ids = [...selected].filter((id) =>
      jobs.some(
        (j) => j.id === id && ["failed", "cancelled"].includes(j.status),
      ),
    );
    await Promise.all(
      ids.map((id) => act(() => resumeReprocessJob(id), id)),
    );
    clearSelection();
  }

  async function deleteSelected() {
    const ids = [...selected].filter((id) => jobs.some((j) => j.id === id));
    await Promise.all(
      ids.map((id) => act(() => deleteReprocessJob(id), id)),
    );
    clearSelection();
  }

  return (
    <section className="detail-card processing-card processing-list-card processing-card-span-full reprocess-jobs-card">
      <div className="processing-card-head processing-card-head--list">
        <div className="processing-card-head-line">
          <div className="processing-card-head-meta">
            <h2>History</h2>
          </div>
          <div className="processing-card-head-search">
            <label
              className="catalog-search-field processing-search-field"
              aria-label="Search history"
            >
              <span className="catalog-search-icon">
                <SearchIcon />
              </span>
              <input
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search"
                autoComplete="off"
              />
            </label>
          </div>
          <div className="processing-card-head-inline-tools">
            <span
              className="catalog-result-count processing-card-title-count"
              aria-label={`${filtered.length} results`}
            >
              {filtered.length}
            </span>
          </div>
          <div className="processing-card-head-actions">
            <div className="reprocess-actions-bar">
              {selectedCount > 0 && (
                <span className="reprocess-bulk-count">
                  {selectedCount} selected
                </span>
              )}
              <button
                type="button"
                className="ghost-button reprocess-bulk-btn"
                disabled={selectedCount === 0}
                onClick={resumeSelected}
              >
                Resume
              </button>
              <button
                type="button"
                className="reprocess-bulk-btn reprocess-bulk-btn--delete"
                disabled={selectedCount === 0}
                onClick={deleteSelected}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="reprocess-empty">
          {q ? "No matching records." : "No history."}
        </p>
      ) : (
        <div className="processing-table-shell" ref={shellRef}>
          <table className="reprocess-table">
            <thead>
              <tr>
                <th className="reprocess-col-check">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    aria-label="Select all"
                  />
                </th>
                <th>Book</th>
                <th className="reprocess-col-status">Status</th>
                <th className="reprocess-col-number reprocess-hide-sm">
                  Retries
                </th>
                <th className="reprocess-col-error reprocess-hide-md">Error</th>
                <th className="reprocess-col-time">Finished</th>
                <th className="reprocess-col-actions" />
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((job) => (
                <tr
                  key={job.id}
                  className={selected.has(job.id) ? "is-selected" : undefined}
                >
                  <td className="reprocess-col-check">
                    <input
                      type="checkbox"
                      checked={selected.has(job.id)}
                      onChange={() => toggleRow(job.id)}
                      aria-label="Select row"
                    />
                  </td>
                  <td>
                    <BookCell job={job} />
                  </td>
                  <td>
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="reprocess-col-number processing-table-muted reprocess-hide-sm">
                    {job.retry_count ?? 0}
                  </td>
                  <td className="reprocess-hide-md">
                    {job.last_error ? (
                      <span
                        className="reprocess-error-text"
                        title={job.last_error}
                      >
                        {job.last_error.length > 72
                          ? `${job.last_error.slice(0, 72)}…`
                          : job.last_error}
                      </span>
                    ) : (
                      <span className="processing-table-muted">—</span>
                    )}
                  </td>
                  <td>
                    <RelTime iso={job.finished_at || job.updated_at} />
                  </td>
                  <td>
                    <div className="reprocess-row-actions">
                      {job.target_book_slug && !job.target_book_deleted && (
                        <BookRouteLink
                          slug={job.target_book_slug}
                          className="ghost-button reprocess-action-btn reprocess-action-btn--open"
                        >
                          Open
                        </BookRouteLink>
                      )}
                      {["failed", "cancelled"].includes(job.status) && (
                        <button
                          type="button"
                          className="ghost-button reprocess-action-btn"
                          disabled={pending.has(job.id)}
                          onClick={() =>
                            act(() => resumeReprocessJob(job.id), job.id)
                          }
                        >
                          Resume
                        </button>
                      )}
                      <button
                        type="button"
                        className="ghost-button reprocess-action-btn reprocess-action-btn--danger"
                        disabled={pending.has(job.id)}
                        onClick={() =>
                          act(() => deleteReprocessJob(job.id), job.id)
                        }
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {hasMore && (
                <tr ref={sentinelRef} aria-hidden="true">
                  <td colSpan={7} className="reprocess-sentinel-cell" />
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function ReprocessingPage() {
  const { activeJobs, historyJobs, summary, loadedOnce, refresh } =
    useReprocessData();

  return (
    <PageFrame pageId="reprocessing" title="Reprocessing">
      <OverviewPanel
        pageId="reprocessing"
        loading={!loadedOnce}
        stats={[
          { id: "queued", label: "Queued", value: summary?.queued ?? 0 },
          { id: "active", label: "Active", value: summary?.active ?? 0 },
          { id: "done", label: "Done", value: summary?.done ?? 0 },
          { id: "failed", label: "Failed", value: summary?.failed ?? 0 },
          { id: "stopped", label: "Stopped", value: summary?.stopped ?? 0 },
        ]}
      />
      <div className="processing-card-grid">
        <ActiveTable jobs={activeJobs} onRefresh={refresh} />
        <HistoryTable jobs={historyJobs} onRefresh={refresh} />
      </div>
    </PageFrame>
  );
}
