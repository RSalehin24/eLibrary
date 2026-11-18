import { Fragment } from "react";
import { Link } from "react-router-dom";
import AsyncButton from "./AsyncButton";
import BookRouteLink from "./BookRouteLink";
import {
  formatBookDate,
  formatBookDateTime,
  getWriterColumnGroups,
  getContributorNamesByRole,
} from "../utils/bookPresentation";
import { CATALOG_TABLE_PREFETCH_TRIGGER } from "../utils/catalogBooks";
import { toQueryString } from "../utils/query";

function renderLinkedValues(values, queryKey, linkFilters) {
  return values.map((value, index) => (
    <Fragment key={`${queryKey}-${value}`}>
      <Link
        to={`/library${toQueryString({ ...(linkFilters || {}), [queryKey]: value })}`}
        className="meta-link"
      >
        {value}
      </Link>
      {index < values.length - 1 ? (
        <span className="meta-divider">, </span>
      ) : null}
    </Fragment>
  ));
}

function renderWriterCell(book, linkFilters, limitContributorRole = false) {
  if (limitContributorRole) {
    const writers = getContributorNamesByRole(book, "author");
    const translators = getContributorNamesByRole(book, "translator");
    const editors = getContributorNamesByRole(book, "editor");

    let selectedGroup = null;
    if (writers.length) {
      selectedGroup = { label: "Writer", names: writers, queryKey: "author" };
    } else if (translators.length) {
      selectedGroup = { label: "Translator", names: translators, queryKey: "contributor" };
    } else if (editors.length) {
      selectedGroup = { label: "Editor", names: editors, queryKey: "contributor" };
    }

    if (!selectedGroup) {
      return <span className="table-muted">—</span>;
    }

    return (
      <div className="table-writer-stack">
        <div className="table-writer-line">
          <span className="table-role-label">{selectedGroup.label}</span>
          <span>
            {renderLinkedValues(selectedGroup.names, selectedGroup.queryKey, linkFilters)}
          </span>
        </div>
      </div>
    );
  }

  const groups = getWriterColumnGroups(book);
  if (!groups.length) {
    return <span className="table-muted">Contributor unavailable</span>;
  }

  return (
    <div className="table-writer-stack">
      {groups.map((group, index) => (
        <div key={`${book.id}-writer-${index}`} className="table-writer-line">
          {group.label ? (
            <span className="table-role-label">{group.label}</span>
          ) : null}
          <span>
            {renderLinkedValues(group.names, group.queryKey, linkFilters)}
          </span>
        </div>
      ))}
    </div>
  );
}

function BookTableSkeletonRows({
  count = 5,
  incremental = false,
  showMyBooksAction = false,
  showPublisher = false,
  hideSeries = false,
  hideType = false,
}) {
  return Array.from({ length: count }, (_, index) => (
    <tr
      key={`${incremental ? "more" : "initial"}-skeleton-${index}`}
      data-testid={
        index === 0
          ? `book-table-${incremental ? "load-more" : "table"}-skeleton`
          : undefined
      }
      aria-hidden="true"
    >
      <td className="table-code-cell">
        <span className="skeleton-line skeleton-line-sm" />
      </td>
      <td className="table-title-cell">
        <div className="book-table-skeleton-stack">
          <span className="skeleton-line skeleton-line-xl" />
          <span className="skeleton-line skeleton-line-sm" />
        </div>
      </td>
      <td>
        <div className="book-table-skeleton-stack">
          <span className="skeleton-line skeleton-line-lg" />
          <span className="skeleton-line skeleton-line-sm" />
        </div>
      </td>
      <td>
        <span className="skeleton-line skeleton-line-sm" />
      </td>
      {!hideSeries ? (
        <td>
          <span className="skeleton-line skeleton-line-sm" />
        </td>
      ) : null}
      {showPublisher ? (
        <td>
          <span className="skeleton-line skeleton-line-sm" />
        </td>
      ) : null}
      {!hideType ? (
        <td>
          <span className="skeleton-pill skeleton-pill-sm" />
        </td>
      ) : null}
      <td>
        <span className="skeleton-line skeleton-line-sm" />
      </td>
      {showMyBooksAction ? (
        <td className="table-action-cell">
          <span className="ghost-button skeleton-button skeleton-button-sm" />
        </td>
      ) : null}
      <td className="table-action-cell">
        <span className="ghost-button skeleton-button skeleton-button-sm" />
      </td>
    </tr>
  ));
}

export default function BookTable({
  books,
  emptyLabel = "No books found.",
  linkFilters = {},
  highlightedBookId = "",
  shellClassName = "",
  shellRef = null,
  hasMore = false,
  observeLoadTrigger = undefined,
  initialLoading = false,
  loadingMore = false,
  refreshing = false,
  showMyBooksAction = false,
  showPublisher = false,
  onMyBooksToggle = null,
  onEditBook = null,
  hideSeries = false,
  hideType = false,
  showTime = false,
  limitContributorRole = false,
  myBooksBusyIds = {},
  sortValue = "",
}) {
  const showInitialSkeleton = (initialLoading || refreshing) && !books?.length;
  const showIncrementalSkeleton = loadingMore && books?.length > 0;
  const columnCount =
    8 +
    (showMyBooksAction ? 1 : 0) +
    (showPublisher ? 1 : 0) -
    (hideSeries ? 1 : 0) -
    (hideType ? 1 : 0);

  const sortKey = sortValue?.replace(/^-/, "") || "";
  const sortDirection = sortValue?.startsWith("-") ? "desc" : "asc";
  const SORT_COLUMN_BY_KEY = {
    title: "title",
    catalog_code: "code",
    created_at: "created",
  };
  const activeSortColumn = SORT_COLUMN_BY_KEY[sortKey] || "";
  function sortIndicator(columnId) {
    if (activeSortColumn !== columnId) return null;
    return (
      <span className="table-sort-indicator" aria-hidden="true">
        {sortDirection === "desc" ? "▼" : "▲"}
      </span>
    );
  }
  function sortAriaSort(columnId) {
    if (activeSortColumn !== columnId) return undefined;
    return sortDirection === "desc" ? "descending" : "ascending";
  }

  return (
    <div
      ref={shellRef}
      className={`catalog-table-shell book-table-shell${
        shellClassName ? ` ${shellClassName}` : ""
      }`}
      aria-busy={initialLoading || loadingMore || refreshing}
    >
      <table
        className={`catalog-table book-table table-mobile-cards${
          showMyBooksAction ? " book-table-with-my-books" : ""
        }`}
      >
        <colgroup>
          <col className="book-table-col-id" />
          <col className="book-table-col-title" />
          <col className="book-table-col-writer" />
          <col className="book-table-col-category" />
          {!hideSeries ? <col className="book-table-col-series" /> : null}
          {showPublisher ? <col className="book-table-col-publisher" /> : null}
          {!hideType ? <col className="book-table-col-type" /> : null}
          <col className="book-table-col-created" />
          {showMyBooksAction ? <col className="book-table-col-action" /> : null}
          <col className="book-table-col-action" />
        </colgroup>
        <thead>
          <tr>
            <th aria-sort={sortAriaSort("code")}>
              Book ID{sortIndicator("code")}
            </th>
            <th aria-sort={sortAriaSort("title")}>
              Title{sortIndicator("title")}
            </th>
            <th>Contributors</th>
            <th>Category</th>
            {!hideSeries ? <th>Series</th> : null}
            {showPublisher ? <th>Publisher</th> : null}
            {!hideType ? <th>Type</th> : null}
            <th aria-sort={sortAriaSort("created")}>
              Created{sortIndicator("created")}
            </th>
            {showMyBooksAction ? <th>My Books</th> : null}
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {showInitialSkeleton ? (
            <BookTableSkeletonRows
              count={5}
              showMyBooksAction={showMyBooksAction}
              showPublisher={showPublisher}
              hideSeries={hideSeries}
              hideType={hideType}
            />
          ) : books?.length ? (
            books.map((book, rowIndex) => {
              const categories = book.categories || [];
              const series = book.series || [];
              const myBooksBusy = Boolean(
                myBooksBusyIds[book.id] || myBooksBusyIds[book.slug],
              );

              return (
                <tr
                  key={book.id}
                  className={
                    highlightedBookId === book.id ? "is-highlighted" : ""
                  }
                  ref={
                    hasMore &&
                    typeof observeLoadTrigger === "function" &&
                    rowIndex ===
                      Math.max(0, books.length - CATALOG_TABLE_PREFETCH_TRIGGER)
                      ? observeLoadTrigger
                      : undefined
                  }
                >
                  <td className="table-code-cell" data-label="Book ID">
                    <BookRouteLink slug={book.slug} className="table-code-link">
                      {book.catalog_code || "Pending"}
                    </BookRouteLink>
                  </td>
                  <td className="table-title-cell" data-label="Title">
                    <BookRouteLink
                      slug={book.slug}
                      className="table-title-link"
                    >
                      {book.title}
                    </BookRouteLink>
                    {book.record_type !== "manual" ? (
                      <span className="table-secondary-line">
                        {book.primary_source?.display_path || "Library record"}
                      </span>
                    ) : null}
                  </td>
                  <td data-label="Contributors">
                    {renderWriterCell(book, linkFilters, limitContributorRole)}
                  </td>
                  <td data-label="Category">
                    {categories.length ? (
                      renderLinkedValues(categories, "category", linkFilters)
                    ) : (
                      <span className="table-muted">Unsorted</span>
                    )}
                  </td>
                  {!hideSeries ? (
                    <td data-label="Series">
                      {series.length ? (
                        renderLinkedValues(series, "series", linkFilters)
                      ) : (
                        <span className="table-muted">Standalone</span>
                      )}
                    </td>
                  ) : null}
                  {showPublisher ? (
                    <td data-label="Publisher">
                      {(() => {
                        const publisherNames = book.publisher
                          ? [book.publisher]
                          : getContributorNamesByRole(book, "publisher");
                        return publisherNames.length ? (
                          renderLinkedValues(publisherNames, "contributor", {
                            ...(linkFilters || {}),
                            contributor_role: "publisher",
                          })
                        ) : (
                          <span className="table-muted">—</span>
                        );
                      })()}
                    </td>
                  ) : null}
                  {!hideType ? (
                    <td data-label="Type">
                      <span
                        className={`table-type-pill table-type-pill-${book.record_type || "digital"}`}
                      >
                        {book.record_type === "manual" ? "Manual" : "Digital"}
                      </span>
                    </td>
                  ) : null}
                  <td data-label="Created">
                    {showTime ? formatBookDateTime(book.created_at) : formatBookDate(book.created_at)}
                  </td>
                  {showMyBooksAction ? (
                    <td className="table-action-cell" data-label="My Books">
                      <AsyncButton
                        className={
                          book.is_in_my_books
                            ? "ghost-button table-row-action my-books-toggle is-in-my-books"
                            : "primary-button table-row-action my-books-toggle"
                        }
                        loading={myBooksBusy}
                        loadingLabel={
                          book.is_in_my_books ? "Removing..." : "Adding..."
                        }
                        onClick={() => onMyBooksToggle?.(book)}
                        disabled={!onMyBooksToggle}
                        aria-label={
                          book.is_in_my_books
                            ? `Remove ${book.title} from My Books`
                            : `Add ${book.title} to My Books`
                        }
                      >
                        {book.is_in_my_books ? "Remove" : "Add"}
                      </AsyncButton>
                    </td>
                  ) : null}
                  <td className="table-action-cell" data-label="Action">
                    {onEditBook ? (
                      <div className="table-actions-group">
                        <BookRouteLink
                          slug={book.slug}
                          className="ghost-button table-row-action"
                        >
                          Open
                        </BookRouteLink>
                        <button
                          type="button"
                          className="ghost-button table-row-action"
                          onClick={() => onEditBook(book)}
                        >
                          Edit
                        </button>
                      </div>
                    ) : (
                      <BookRouteLink
                        slug={book.slug}
                        className="ghost-button table-row-action"
                      >
                        Open
                      </BookRouteLink>
                    )}
                  </td>
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan={columnCount} className="table-empty-cell">
                {emptyLabel}
              </td>
            </tr>
          )}
          {showIncrementalSkeleton ? (
            <BookTableSkeletonRows
              count={5}
              incremental={true}
              showMyBooksAction={showMyBooksAction}
              showPublisher={showPublisher}
              hideSeries={hideSeries}
              hideType={hideType}
            />
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
