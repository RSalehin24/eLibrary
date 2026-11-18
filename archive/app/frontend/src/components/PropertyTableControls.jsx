import { useEffect, useMemo, useState } from "react";

export const PROPERTY_TABLE_ROW_OPTIONS = [5, 10, 20, 35, 50, 100];

function getPageLabel(page, pageCount) {
  return `Page ${page} / ${pageCount}`;
}

export function useClientPagination(
  items,
  initialRowsPerPage = PROPERTY_TABLE_ROW_OPTIONS[0],
) {
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPageState] = useState(initialRowsPerPage);

  const pagination = useMemo(() => {
    const totalCount = items.length;
    const pageCount = Math.max(1, Math.ceil(totalCount / rowsPerPage));
    const currentPage = Math.min(Math.max(page, 1), pageCount);
    const startIndex = (currentPage - 1) * rowsPerPage;

    return {
      items: items.slice(startIndex, startIndex + rowsPerPage),
      page: currentPage,
      pageCount,
      rowsPerPage,
      totalCount,
      hasPrevious: currentPage > 1,
      hasNext: currentPage < pageCount,
    };
  }, [items, page, rowsPerPage]);

  useEffect(() => {
    setPage((currentPage) => {
      const nextPageCount = Math.max(1, Math.ceil(items.length / rowsPerPage));
      return Math.min(Math.max(currentPage, 1), nextPageCount);
    });
  }, [items.length, rowsPerPage]);

  function setRowsPerPage(nextValue) {
    setRowsPerPageState(Number(nextValue) || initialRowsPerPage);
    setPage(1);
  }

  function resetPage() {
    setPage(1);
  }

  return {
    ...pagination,
    setPage,
    setRowsPerPage,
    resetPage,
  };
}

export default function PropertyTableControls({
  sortValue,
  sortOptions,
  onSortChange,
  rowsPerPage,
  onRowsPerPageChange,
  page,
  pageCount,
  hasPrevious,
  hasNext,
  onPageChange,
  disabled = false,
  leadingContent = null,
}) {
  const hasSort = Boolean(sortOptions?.length);
  const controls = (
    <div
      className={`catalog-toolbar-secondary property-table-controls${
        hasSort ? "" : " property-table-controls--without-sort"
      }`}
    >
      {hasSort ? (
        <label className="catalog-toolbar-field catalog-toolbar-field-sort">
          <span className="fact-label catalog-toolbar-inline-label">Sort</span>
          <select
            className="catalog-toolbar-select"
            value={sortValue}
            onChange={(event) => onSortChange?.(event.target.value)}
            disabled={disabled}
          >
            {sortOptions.map((option) => (
              <option key={`sort-${option.value}`} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <label className="catalog-toolbar-field catalog-toolbar-field-rows">
        <span className="fact-label catalog-toolbar-inline-label">Rows</span>
        <select
          className="catalog-toolbar-select"
          value={String(rowsPerPage)}
          onChange={(event) =>
            onRowsPerPageChange(Number(event.target.value) || rowsPerPage)
          }
          disabled={disabled}
        >
          {PROPERTY_TABLE_ROW_OPTIONS.map((option) => (
            <option key={`rows-${option}`} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
      <div className="catalog-pagination">
        <span className="catalog-page-indicator">
          {getPageLabel(page, pageCount)}
        </span>
        <div className="catalog-pagination-actions">
          <button
            type="button"
            className="ghost-button"
            onClick={() => onPageChange(1)}
            disabled={disabled || !hasPrevious}
          >
            First
          </button>
          <button
            type="button"
            className="ghost-button"
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={disabled || !hasPrevious}
          >
            Prev
          </button>
          <button
            type="button"
            className="ghost-button"
            onClick={() => onPageChange(page + 1)}
            disabled={disabled || !hasNext}
          >
            Next
          </button>
          <button
            type="button"
            className="ghost-button"
            onClick={() => onPageChange(pageCount)}
            disabled={disabled || !hasNext}
          >
            Last
          </button>
        </div>
      </div>
    </div>
  );

  if (!leadingContent) {
    return controls;
  }

  return (
    <div className="property-table-toolbar-layout">
      <div className="property-table-toolbar-leading">{leadingContent}</div>
      {controls}
    </div>
  );
}
