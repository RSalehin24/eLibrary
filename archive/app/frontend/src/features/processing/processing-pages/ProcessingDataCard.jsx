import { useEffect, useMemo, useState } from "react";
import AsyncButton from "../../../components/AsyncButton";
import LoadingSpinner from "../../../components/LoadingSpinner";
import { ProcessingCountSkeleton } from "../../../components/ProcessingCardSkeleton";
import {
  countActiveFilters,
  renderField,
} from "../../../components/catalog-toolbar/fields.jsx";
import {
  FilterIcon,
  SearchIcon,
} from "../../../components/catalog-toolbar/icons.jsx";
import { useBookProcessing } from "../BookProcessingStore";
import { REQUEST_STATE_LABELS } from "../types";
import {
  PROCESSING_TABLE_PREFETCH_TRIGGER,
  SEARCH_PLACEHOLDER,
  formatDate,
  requestDetails,
} from "./processingPageModel";
import {
  ActiveFilters,
  ContributorsCell,
  MultiPageTocBadge,
} from "./processingPagePrimitives";
import { processingCardCountFromState } from "./processingCardState";
import { TableSkeletonRows } from "./TableSkeletonRows";
import { useProcessingTableData } from "./useProcessingTableData";
export function ProcessingDataCard({
  pageId,
  cardId,
  cardKey,
  title,
  actions = [],
  busy = false,
  readOnly = false,
  detailsLabel = "Details",
  showDetailsColumn = true,
  emptyLabel = "No records.",
  className = "",
  fullSpan = false,
  bookColumnMode = "combined",
  actionLabel = "Action",
  renderRowAction = null,
  countPlacement = "title",
}) {
  const [selectedIds, setSelectedIds] = useState([]);
  const [filters, setFilters] = useState({
    q: "",
    category: "",
    status: "",
  });
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const { canLoadProcessingState, processingState } = useBookProcessing();
  const showSelectionColumn = actions.length > 0 && !readOnly;
  const splitBookColumn = bookColumnMode === "split";
  const showActionColumn = typeof renderRowAction === "function";
  const defaultFilters = useMemo(
    () => ({
      q: "",
      category: "",
      status: "",
    }),
    [],
  );
  const {
    rows,
    totalCount,
    categoryOptions,
    statusOptions,
    hasMore,
    loadedOnce,
    initialLoading,
    loadingMore,
    refreshing,
    error: tableError,
    setCardVisibilityNode,
    tableShellRef,
    observeLoadTrigger,
  } = useProcessingTableData({
    cardKey,
    filters,
    enabled: canLoadProcessingState,
  });
  const filterFields = useMemo(
    () => [
      {
        key: "category",
        label: "Category",
        testId: `${pageId}-${cardId}-category-filter`,
        type: "select",
        options: [
          {
            value: "",
            label: "All categories",
          },
          ...categoryOptions.map((category) => ({
            value: category,
            label: category,
          })),
        ],
      },
      {
        key: "status",
        label: "Status",
        testId: `${pageId}-${cardId}-status-filter`,
        type: "select",
        options: [
          {
            value: "",
            label: "All statuses",
          },
          ...statusOptions.map((status) => ({
            value: status,
            label: REQUEST_STATE_LABELS[status] || status,
          })),
        ],
      },
    ],
    [cardId, categoryOptions, pageId, statusOptions],
  );
  const activeFilterCount = useMemo(
    () => countActiveFilters(filters, filterFields, defaultFilters),
    [defaultFilters, filterFields, filters],
  );
  const sharedCount = useMemo(
    () =>
      !filters.q && !filters.category && !filters.status
        ? processingCardCountFromState(cardKey, processingState)
        : null,
    [cardKey, filters.category, filters.q, filters.status, processingState],
  );
  const visibleRows = rows;
  const visibleColumnCount =
    (showSelectionColumn ? 1 : 0) +
    (splitBookColumn ? 6 : 5) +
    (showDetailsColumn ? 1 : 0) +
    (showActionColumn ? 1 : 0);
  const showInitialTableSkeleton =
    initialLoading || (!loadedOnce && Number(sharedCount) > 0);
  const showRefreshSkeletonRows = loadingMore && visibleRows.length > 0;
  const countValue =
    loadedOnce || sharedCount === null ? totalCount : sharedCount;
  useEffect(() => {
    const visibleIds = new Set(visibleRows.map((row) => row.id));
    setSelectedIds((current) => current.filter((id) => visibleIds.has(id)));
  }, [visibleRows]);
  const selectedRows = visibleRows.filter((row) =>
    selectedIds.includes(row.id),
  );
  const selectableRows = visibleRows.filter((row) => row.selectable);
  const allSelectableSelected =
    selectableRows.length > 0 &&
    selectableRows.every((row) => selectedIds.includes(row.id));
  function toggleRow(rowId, checked) {
    setSelectedIds((current) => {
      if (checked) {
        return current.includes(rowId) ? current : [...current, rowId];
      }
      return current.filter((id) => id !== rowId);
    });
  }
  function toggleAll(checked) {
    if (!checked) {
      setSelectedIds([]);
      return;
    }
    setSelectedIds(selectableRows.map((row) => row.id));
  }
  async function runAction(action) {
    const ids = selectedRows.map((row) => row.id);
    const result = await action.onAction(ids, selectedRows);
    if (result) {
      setSelectedIds([]);
    }
  }
  function handleQueryChange(event) {
    const nextQuery = event.target.value;
    setFilters((current) => ({
      ...current,
      q: nextQuery,
    }));
  }
  const bulkActions = actions.length ? (
    <div className="processing-bulk-actions">
      {actions.map((action) => (
        <AsyncButton
          key={action.id}
          type="button"
          className={
            action.danger ? "ghost-button danger-button" : "primary-button"
          }
          disabled={initialLoading || selectedRows.length === 0}
          loading={busy}
          loadingLabel="Working"
          onClick={() => runAction(action)}
          data-testid={`${pageId}-${cardId}-${action.id}-btn`}
        >
          {action.label}
          {selectedRows.length ? ` (${selectedRows.length})` : ""}
        </AsyncButton>
      ))}
    </div>
  ) : null;
  const countBadge = (
    <span
      className="catalog-result-count processing-card-title-count"
      aria-label={`${countValue} results`}
      data-testid={`${pageId}-${cardId}-count`}
    >
      {showInitialTableSkeleton && sharedCount === null ? (
        <ProcessingCountSkeleton />
      ) : (
        countValue
      )}
    </span>
  );
  return (
    <section
      ref={setCardVisibilityNode}
      className={`detail-card processing-card processing-list-card processing-replacement-card${fullSpan ? " processing-card-span-full" : ""}${className ? ` ${className}` : ""}`}
      data-testid={`${pageId}-${cardId}-card`}
    >
      <div className="processing-card-head processing-card-head--list">
        <div className="processing-card-head-line">
          <div className="processing-card-head-meta">
            <div className="processing-card-title-row">
              <h2>{title}</h2>
              {countPlacement === "title" ? countBadge : null}
            </div>
          </div>
          <div className="processing-card-head-search">
            <label
              className="catalog-search-field processing-search-field"
              aria-label={SEARCH_PLACEHOLDER}
            >
              <span className="catalog-search-icon">
                <SearchIcon />
              </span>
              <input
                type="search"
                value={filters.q || ""}
                onChange={handleQueryChange}
                placeholder={SEARCH_PLACEHOLDER}
                autoComplete="off"
                data-testid={`${pageId}-${cardId}-search`}
                disabled={busy}
              />
            </label>
          </div>
          <div className="processing-card-head-inline-tools">
            <button
              type="button"
              className={`catalog-filter-toggle${filtersExpanded ? " is-active" : ""}`}
              onClick={() => setFiltersExpanded((current) => !current)}
              aria-expanded={filtersExpanded}
              aria-controls={`${pageId}-${cardId}-filters`}
              disabled={busy || showInitialTableSkeleton}
            >
              <FilterIcon />
              <span>Filters</span>
              {activeFilterCount ? (
                <span className="catalog-filter-count">
                  {activeFilterCount}
                </span>
              ) : null}
            </button>
            {countPlacement === "inline-tools" ? countBadge : null}
          </div>
          {bulkActions ? (
            <div className="processing-card-head-actions">{bulkActions}</div>
          ) : null}
        </div>
      </div>

      <div
        id={`${pageId}-${cardId}-filters`}
        className={`catalog-filter-drawer processing-filter-drawer${filtersExpanded ? " is-open" : ""}`}
        aria-hidden={filtersExpanded ? "false" : "true"}
      >
        <div className="catalog-filter-grid processing-filter-grid">
          {filterFields.map((field) => (
            <label key={field.key} className="catalog-filter-field">
              <span className="fact-label">{field.label}</span>
              {renderField(field, filters, setFilters)}
            </label>
          ))}
        </div>
      </div>
      <ActiveFilters
        pageId={pageId}
        cardId={cardId}
        categoryFilter={filters.category}
        statusFilter={filters.status}
      />

      {busy ? (
        <div className="processing-bulk-bar">
          <div className="processing-bulk-status">
            <span
              className="processing-inline-loader"
              data-testid={`${pageId}-${cardId}-loader`}
            >
              <LoadingSpinner size={14} /> Working
            </span>
          </div>
        </div>
      ) : null}

      <div
        ref={tableShellRef}
        className="processing-table-shell processing-table-shell--mobile-cards"
        aria-busy={initialLoading || loadingMore}
      >
        <table
          className="simple-table processing-table table-mobile-cards"
          data-testid={`${pageId}-${cardId}-table`}
        >
          <colgroup>
            {showSelectionColumn ? (
              <col className="processing-col-select" />
            ) : null}
            {splitBookColumn ? (
              <>
                <col className="processing-col-name" />
                <col className="processing-col-url" />
              </>
            ) : (
              <col className="processing-col-book-wide" />
            )}
            <col className="processing-col-contributors-wide" />
            <col className="processing-col-category" />
            <col className="processing-col-status" />
            {showDetailsColumn ? (
              <col className="processing-col-details" />
            ) : null}
            <col className="processing-col-updated" />
            {showActionColumn ? (
              <col className="processing-col-action" />
            ) : null}
          </colgroup>
          <thead>
            <tr>
              {showSelectionColumn ? (
                <th className="processing-col-select">
                  <input
                    type="checkbox"
                    className="processing-checkbox"
                    aria-label={`Select all ${title}`}
                    checked={allSelectableSelected}
                    disabled={
                      busy ||
                      showInitialTableSkeleton ||
                      selectableRows.length === 0
                    }
                    onChange={(event) => toggleAll(event.target.checked)}
                    data-testid={`${pageId}-${cardId}-select-all`}
                  />
                </th>
              ) : null}
              {splitBookColumn ? (
                <>
                  <th className="processing-col-name">Name</th>
                  <th className="processing-col-url">URL</th>
                </>
              ) : (
                <th className="processing-col-book-wide">Book</th>
              )}
              <th className="processing-col-contributors-wide">Credits</th>
              <th className="processing-col-category">Category</th>
              <th className="processing-col-status">Status</th>
              {showDetailsColumn ? (
                <th className="processing-col-details">{detailsLabel}</th>
              ) : null}
              <th className="processing-col-updated">Updated</th>
              {showActionColumn ? (
                <th className="processing-col-action">{actionLabel}</th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {showInitialTableSkeleton ? (
              <TableSkeletonRows
                pageId={pageId}
                cardId={cardId}
                showSelectionColumn={showSelectionColumn}
                splitBookColumn={splitBookColumn}
                showDetailsColumn={showDetailsColumn}
                showActionColumn={showActionColumn}
              />
            ) : visibleRows.length ? (
              visibleRows.map((row, rowIndex) => (
                <tr
                  key={row.id}
                  data-testid={`${pageId}-${cardId}-row-${row.id}`}
                  ref={
                    hasMore &&
                    rowIndex ===
                      Math.max(
                        0,
                        visibleRows.length - PROCESSING_TABLE_PREFETCH_TRIGGER,
                      )
                      ? observeLoadTrigger
                      : undefined
                  }
                >
                  {showSelectionColumn ? (
                    <td className="processing-col-select" data-label="Select">
                      <input
                        type="checkbox"
                        className="processing-checkbox"
                        aria-label={`Select ${row.title}`}
                        checked={selectedIds.includes(row.id)}
                        disabled={busy || !row.selectable}
                        onChange={(event) =>
                          toggleRow(row.id, event.target.checked)
                        }
                        data-testid={`${pageId}-${cardId}-select-${row.id}`}
                      />
                    </td>
                  ) : null}
                  {splitBookColumn ? (
                    <>
                      <td className="processing-col-name" data-label="Name">
                        <div className="processing-table-primary">
                          <strong>{row.title}</strong>
                          <MultiPageTocBadge row={row} />
                        </div>
                      </td>
                      <td className="processing-col-url" data-label="URL">
                        {row.url ? (
                          <span className="processing-table-link">
                            {row.displayUrl || row.url}
                          </span>
                        ) : (
                          <span className="processing-table-muted">-</span>
                        )}
                      </td>
                    </>
                  ) : (
                    <td className="processing-col-book-wide" data-label="Book">
                      <div className="processing-table-primary">
                        <strong>{row.title}</strong>
                        <MultiPageTocBadge row={row} />
                        {row.url ? (
                          <span className="processing-table-secondary">
                            {row.displayUrl || row.url}
                          </span>
                        ) : null}
                      </div>
                    </td>
                  )}
                  <td
                    className="processing-col-contributors-wide"
                    data-label="Credits"
                  >
                    <ContributorsCell row={row} />
                  </td>
                  <td className="processing-col-category" data-label="Category">
                    {row.category || "Uncategorized"}
                  </td>
                  <td className="processing-col-status" data-label="Status">
                    {REQUEST_STATE_LABELS[row.status] || row.status}
                  </td>
                  {showDetailsColumn ? (
                    <td
                      className="processing-col-details"
                      data-label={detailsLabel}
                    >
                      {requestDetails(row) || "Ready"}
                    </td>
                  ) : null}
                  <td className="processing-col-updated" data-label="Updated">
                    {formatDate(row.updatedAt)}
                  </td>
                  {showActionColumn ? (
                    <td
                      className="processing-col-action"
                      data-label={actionLabel}
                    >
                      {renderRowAction(row) || (
                        <span className="processing-table-muted">-</span>
                      )}
                    </td>
                  ) : null}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={visibleColumnCount} className="table-empty-cell">
                  {tableError || emptyLabel}
                </td>
              </tr>
            )}
            {showRefreshSkeletonRows ? (
              <TableSkeletonRows
                pageId={pageId}
                cardId={cardId}
                showSelectionColumn={showSelectionColumn}
                splitBookColumn={splitBookColumn}
                showDetailsColumn={showDetailsColumn}
                showActionColumn={showActionColumn}
                count={3}
                incremental
              />
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
