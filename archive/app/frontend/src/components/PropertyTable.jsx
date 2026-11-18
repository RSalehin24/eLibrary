import { Children, cloneElement, isValidElement } from "react";
import { CATALOG_TABLE_PREFETCH_TRIGGER } from "../utils/catalogBooks";

function PropertyTableSkeletonRows({
  columnKinds,
  count = 5,
  incremental = false,
}) {
  return Array.from({ length: count }, (_, rowIndex) => (
    <tr
      key={`${incremental ? "more" : "initial"}-property-skeleton-${rowIndex}`}
      data-testid={
        rowIndex === 0
          ? `property-table-${incremental ? "load-more" : "table"}-skeleton`
          : undefined
      }
      aria-hidden="true"
    >
      {columnKinds.map((kind, columnIndex) => (
        <td
          key={`property-skeleton-${rowIndex}-${columnIndex}`}
          className={
            kind === "action"
              ? "table-action-cell"
              : kind === "code"
                ? "table-code-cell"
                : undefined
          }
        >
          {kind === "action" ? (
            <span className="ghost-button skeleton-button skeleton-button-sm" />
          ) : kind === "title" ? (
            <span className="skeleton-line skeleton-line-lg" />
          ) : (
            <span className="skeleton-line skeleton-line-sm" />
          )}
        </td>
      ))}
    </tr>
  ));
}

function clonePropertyRow(row, headers, rowRef = undefined) {
  if (!isValidElement(row)) {
    return row;
  }

  if (row.type !== "tr") {
    return rowRef ? cloneElement(row, { ref: rowRef }) : row;
  }

  let headerIndex = 0;
  const children = Children.map(row.props.children, (cell) => {
    if (!isValidElement(cell) || cell.type !== "td") {
      return cell;
    }

    const dataLabel = cell.props["data-label"] || headers[headerIndex];
    headerIndex += 1;

    return dataLabel
      ? cloneElement(cell, { "data-label": dataLabel })
      : cell;
  });

  return cloneElement(row, rowRef ? { ref: rowRef } : null, children);
}

export default function PropertyTable({
  headers,
  columnKinds,
  items,
  renderRow,
  emptyLabel,
  shellRef = null,
  hasMore = false,
  observeLoadTrigger = undefined,
  initialLoading = false,
  loadingMore = false,
  refreshing = false,
  shellClassName = "",
  tableClassName = "",
}) {
  const showInitialSkeleton = (initialLoading || refreshing) && !items.length;
  const showIncrementalSkeleton = loadingMore && items.length > 0;
  const tableClasses = [
    "catalog-table",
    "property-table",
    "table-mobile-cards",
    tableClassName,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      ref={shellRef}
      className={`catalog-table-shell${shellClassName ? ` ${shellClassName}` : ""}`}
      aria-busy={initialLoading || loadingMore || refreshing}
    >
      <table className={tableClasses}>
        <colgroup>
          {columnKinds.map((kind, index) => (
            <col key={`${kind}-${index}`} className={`property-table-col-${kind}`} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {showInitialSkeleton ? (
            <PropertyTableSkeletonRows columnKinds={columnKinds} />
          ) : items.length ? (
            items.map((item, rowIndex) => {
              const row = renderRow(item, rowIndex);
              const shouldObserveRow =
                hasMore &&
                typeof observeLoadTrigger === "function" &&
                rowIndex ===
                  Math.max(0, items.length - CATALOG_TABLE_PREFETCH_TRIGGER);

              return clonePropertyRow(
                row,
                headers,
                shouldObserveRow ? observeLoadTrigger : undefined,
              );
            })
          ) : (
            <tr>
              <td colSpan={headers.length} className="table-empty-cell">
                {emptyLabel}
              </td>
            </tr>
          )}
          {showIncrementalSkeleton ? (
            <PropertyTableSkeletonRows
              columnKinds={columnKinds}
              count={3}
              incremental
            />
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
