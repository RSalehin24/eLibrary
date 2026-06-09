import { Fragment } from "react";
import { Link } from "react-router-dom";
import BookRouteLink from "./BookRouteLink";
import BookCoverArt from "./BookCoverArt";
import LoadingSpinner from "./LoadingSpinner";
import { SendToKindleIcon, SentToKindleIcon } from "./KindleIcons";
import {
  formatBookDate,
  getWriterColumnGroups
} from "../utils/bookPresentation";
import { toQueryString } from "../utils/query";

function renderFilterLinks(values, queryKey, emptyLabel) {
  if (!values?.length) {
    return emptyLabel;
  }

  return values.map((value, index) => (
    <Fragment key={`${queryKey}-${value}`}>
      <Link to={`/library${toQueryString({ [queryKey]: value })}`} className="meta-link">
        {value}
      </Link>
      {index < values.length - 1 ? <span className="meta-divider">, </span> : null}
    </Fragment>
  ));
}

function RemoveIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        d="M5.25 5.25l9.5 9.5M14.75 5.25l-9.5 9.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        d="M10 4v12M4 10h12"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        d="M4 10l4 4 8-8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function BookCard({
  book,
  cardRef = undefined,
  onRemoveFromMyBooks = null,
  removing = false,
  onMyBooksToggle = null,
  onSendToKindle = null,
  sendingToKindle = false,
  hasKindleEmail = false,
}) {
  const contributorGroups = getWriterColumnGroups(book);
  const series = book.series || [];
  const categories = book.categories || [];
  const bookIdLabel = book.catalog_code || "Pending";
  const addedAt = book.my_books_added_at || book.latest_submission_at;
  const hasSentToKindle = Boolean(book.last_kindle_sent_at);

  return (
    <article className="book-card" ref={cardRef}>
      {onRemoveFromMyBooks ? (
        <button
          type="button"
          className="book-card-remove-button"
          onClick={() => onRemoveFromMyBooks(book)}
          disabled={removing}
          aria-busy={removing ? "true" : undefined}
          aria-label={`Remove ${book.title} from My Books`}
          title="Remove from My Books"
        >
          {removing ? <LoadingSpinner size={16} /> : <RemoveIcon />}
        </button>
      ) : null}
      <div className="book-card-art">
        {(onMyBooksToggle || (hasKindleEmail && book.has_epub_asset)) ? (
          <div className="book-card-action-wrapper">
            {hasKindleEmail && book.has_epub_asset ? (
              <div className="book-card-action-slot">
                <button
                  type="button"
                  className={`book-card-kindle-button${hasSentToKindle ? " is-sent" : ""}`}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onSendToKindle?.(book);
                  }}
                  disabled={sendingToKindle}
                  aria-busy={sendingToKindle ? "true" : undefined}
                  aria-label={hasSentToKindle ? `Resend ${book.title} to Kindle` : `Send ${book.title} to Kindle`}
                  title={hasSentToKindle ? "Resend to Kindle" : "Send to Kindle"}
                >
                  {sendingToKindle ? (
                    <LoadingSpinner size={16} />
                  ) : hasSentToKindle ? (
                    <SentToKindleIcon />
                  ) : (
                    <SendToKindleIcon />
                  )}
                </button>
              </div>
            ) : null}
            {onMyBooksToggle ? (
              <div className="book-card-action-slot">
                <button
                  type="button"
                  className={`book-card-toggle-button ${book.is_in_my_books ? "is-added" : ""}`}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onMyBooksToggle(book);
                  }}
                  disabled={removing}
                  aria-busy={removing ? "true" : undefined}
                  aria-label={
                    book.is_in_my_books
                      ? `Remove ${book.title} from My Books`
                      : `Add ${book.title} to My Books`
                  }
                  title={book.is_in_my_books ? "Remove from My Books" : "Add to My Books"}
                >
                  {removing ? (
                    <LoadingSpinner size={16} />
                  ) : book.is_in_my_books ? (
                    <CheckIcon />
                  ) : (
                    <PlusIcon />
                  )}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
        <BookCoverArt book={book} className="book-card-cover" ariaHidden />
      </div>

      <div className="book-card-body">
        <div className="book-card-topline">
          <p className="book-card-id">{bookIdLabel}</p>
        </div>

        <div className="book-card-heading">
          <h3>{book.title}</h3>
          <div className="book-card-contributors book-card-contributor-groups">
            {contributorGroups.length ? (
              contributorGroups.map((group, index) => (
                <div key={`${book.id}-contributor-${index}`} className="table-writer-line">
                  {group.label ? <span className="table-role-label">{group.label}</span> : null}
                  <span className="book-meta">{renderFilterLinks(group.names, group.queryKey, "Contributor unavailable")}</span>
                </div>
              ))
            ) : (
              <p className="book-meta">Contributor unavailable</p>
            )}
          </div>
        </div>

        <div className="book-card-details">
          <div className="book-detail-chip">
            <span className="fact-label">Categories</span>
            <strong>{renderFilterLinks(categories, "category", "Unsorted")}</strong>
          </div>
          <div className="book-detail-chip">
            <span className="fact-label">Series</span>
            <strong>{renderFilterLinks(series, "series", "Standalone")}</strong>
          </div>
        </div>

        <div className="book-card-footer">
          <div className="book-meta-stack">
            <p className="book-timestamp">{book.record_type === "manual" ? "Manual entry" : "Library record"}</p>
            {addedAt ? <p className="book-timestamp">Added on {formatBookDate(addedAt)}</p> : null}
          </div>
          <BookRouteLink
            slug={book.slug}
            className="primary-button book-card-action"
          >
            Open record
          </BookRouteLink>
        </div>
      </div>
    </article>
  );
}
