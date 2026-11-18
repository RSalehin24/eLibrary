export function TableSkeletonRows({
  pageId,
  cardId,
  showSelectionColumn,
  splitBookColumn,
  showDetailsColumn = true,
  showActionColumn = false,
  count = 5,
  incremental = false
}) {
  return Array.from({
    length: count
  }, (_, index) => <tr key={`${incremental ? "more" : "initial"}-skeleton-${index}`} className={`processing-skeleton-row processing-table-skeleton-row${splitBookColumn ? " processing-skeleton-row--split" : ""}`} data-testid={index === 0 ? `${pageId}-${cardId}-${incremental ? "load-more" : "table"}-skeleton` : undefined} aria-hidden="true">
      {showSelectionColumn ? <td className="processing-col-select">
          <span className="processing-checkbox-skeleton processing-skeleton-control" />
        </td> : null}
      {splitBookColumn ? <>
          <td className="processing-col-name">
            <div className="processing-table-primary">
              <strong>
                <span className="skeleton-line skeleton-line-xl" />
              </strong>
            </div>
          </td>
          <td className="processing-col-url">
            <span className="processing-table-link">
              <span className="processing-table-skeleton-stack">
                <span className="skeleton-line skeleton-line-lg" />
                <span className="skeleton-line skeleton-line-sm" />
              </span>
            </span>
          </td>
        </> : <td className="processing-col-book-wide">
          <div className="processing-table-skeleton-stack">
            <span className="skeleton-line skeleton-line-xl" />
            <span className="skeleton-line skeleton-line-sm" />
          </div>
        </td>}
      <td className="processing-col-contributors-wide">
        <div className="processing-contributors-list" style={splitBookColumn ? {
        minHeight: "81px"
      } : undefined}>
          <div className="processing-contributor-entry">
            <span className="processing-contributor-label">
              <span className="skeleton-line skeleton-line-sm" />
            </span>
            <span className="processing-table-muted">
              <span className="skeleton-line skeleton-line-sm" />
            </span>
          </div>
          <div className="processing-contributor-entry">
            <span className="processing-contributor-label">
              <span className="skeleton-line skeleton-line-sm" />
            </span>
            <span className="processing-table-muted">
              <span className="skeleton-line skeleton-line-sm" />
            </span>
          </div>
        </div>
      </td>
      <td className="processing-col-category">
        <span className="skeleton-line skeleton-line-sm" />
      </td>
      <td className="processing-col-status">
        <span className="skeleton-line skeleton-line-sm" />
      </td>
      {showDetailsColumn ? <td className="processing-col-details">
          <span className="skeleton-line skeleton-line-lg" />
        </td> : null}
      <td className="processing-col-updated">
        <span className="skeleton-line skeleton-line-sm" />
      </td>
      {showActionColumn ? <td className="processing-col-action">
          <span className="ghost-button skeleton-button skeleton-button-sm" />
        </td> : null}
    </tr>);
}
