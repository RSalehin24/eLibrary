import AsyncButton from "../../../components/AsyncButton";
import BookCoverArt from "../../../components/BookCoverArt";
import LoadingSpinner from "../../../components/LoadingSpinner";
import StatusPill from "../../../components/StatusPill";
import { assetLabels } from "../constants";
import { RefreshIcon, TrashIcon } from "./BookDetailIcons";
import BookFilterLinkList from "./BookFilterLinkList";

export default function BookDetailHero({
  actions,
  assetLoadingCounts,
  book,
  bookIdValue,
  bookLinkFilters,
  canEditMetadata,
  deleting,
  detail,
  epubInputRef,
  hasKindleEmail,
  hasSentToKindle,
  htmlPreviewLockedByAssetId,
  launchingReader,
  pickingEpub,
  primaryContributorGroup,
  regenerating,
  replacingEpub,
  sendingToKindle,
  supportingContributorGroups,
}) {
  return (
    <section className="detail-card book-hero" data-testid="book-detail-hero">
      {canEditMetadata ? (
        <div className="book-hero-controls">
          <button
            type="button"
            data-testid="book-regenerate-button"
            className="book-refresh-control"
            onClick={actions.regenerateBook}
            aria-label={
              detail.hasActiveProcessing
                ? "Book regeneration in progress"
                : "Regenerate book"
            }
            title={
              detail.hasActiveProcessing
                ? "Book regeneration in progress"
                : "Regenerate book"
            }
            disabled={regenerating || detail.hasActiveProcessing}
          >
            <RefreshIcon
              spinning={regenerating || detail.hasActiveProcessing}
            />
          </button>
          <button
            type="button"
            data-testid="book-delete-button"
            className="book-delete-control"
            onClick={actions.requestDeleteBook}
            aria-label={deleting ? "Deleting book" : "Delete book"}
            title={deleting ? "Deleting book" : "Delete book"}
            disabled={deleting || detail.hasActiveProcessing}
          >
            {deleting ? <LoadingSpinner size={18} /> : <TrashIcon />}
          </button>
        </div>
      ) : null}

      <div className="book-hero-cover">
        <BookCoverArt
          book={book}
          className="book-cover-large book-hero-placeholder"
          ariaHidden
        />
      </div>

      <div className="book-hero-copy">
        <strong className="book-hero-id">{bookIdValue}</strong>
        <h1>{book.title}</h1>
        {primaryContributorGroup ? (
          primaryContributorGroup.role === "author" ? (
            <p className="detail-lead">
              <BookFilterLinkList
                values={primaryContributorGroup.names}
                queryKey="author"
                emptyLabel="Contributor unavailable"
                extraFilters={bookLinkFilters}
              />
            </p>
          ) : (
            <p className="detail-meta-row detail-lead-row">
              <span className="fact-label">
                {primaryContributorGroup.label}
              </span>
              <span className="detail-meta-values">
                <BookFilterLinkList
                  values={primaryContributorGroup.names}
                  queryKey="contributor"
                  emptyLabel="Contributor unavailable"
                  extraFilters={bookLinkFilters}
                />
              </span>
            </p>
          )
        ) : (
          <p className="detail-lead">Contributor unavailable</p>
        )}

        <div className="detail-statuses">
          <StatusPill value={book.state} />
          <StatusPill value={book.review_state} />
        </div>

        {supportingContributorGroups.length ||
        book.series?.length ||
        book.categories?.length ? (
          <div className="book-meta-stack">
            {supportingContributorGroups.map((group) => (
              <p key={group.role} className="detail-meta-row">
                <span className="fact-label">{group.label}</span>
                <span className="detail-meta-values">
                  <BookFilterLinkList
                    values={group.names}
                    queryKey={
                      group.role === "author" ? "author" : "contributor"
                    }
                    extraFilters={bookLinkFilters}
                  />
                </span>
              </p>
            ))}
            {book.series?.length ? (
              <p className="detail-meta-row">
                <span className="fact-label">Series</span>
                <span className="detail-meta-values">
                  <BookFilterLinkList
                    values={book.series}
                    queryKey="series"
                    extraFilters={bookLinkFilters}
                  />
                </span>
              </p>
            ) : null}
            {book.categories?.length ? (
              <p className="detail-meta-row">
                <span className="fact-label">Categories</span>
                <span className="detail-meta-values">
                  <BookFilterLinkList
                    values={book.categories}
                    queryKey="category"
                    extraFilters={bookLinkFilters}
                  />
                </span>
              </p>
            ) : null}
          </div>
        ) : null}

        <div className="book-hero-actions">
          <AsyncButton
            type="button"
            data-testid="book-open-reader-button"
            className="primary-button"
            onClick={actions.launchReader}
            loading={launchingReader}
            loadingLabel="Opening..."
            disabled={book && book.can_launch_reader === false}
          >
            Open reader
          </AsyncButton>
          <AsyncButton
            data-testid="book-my-books-button"
            className={
              book.is_in_my_books
                ? "ghost-button book-my-books-button is-in-my-books"
                : "primary-button book-my-books-button"
            }
            onClick={actions.toggleMyBooks}
            loading={actions.togglingMyBooks}
            loadingLabel={book.is_in_my_books ? "Removing..." : "Adding..."}
          >
            {book.is_in_my_books ? "Remove from My Books" : "Add to My Books"}
          </AsyncButton>
          {detail.epubAsset && hasKindleEmail ? (
            <AsyncButton
              type="button"
              data-testid="book-send-to-kindle-button"
              className={hasSentToKindle ? "resend-kindle-button" : "ghost-button"}
              onClick={actions.sendToKindle}
              disabled={sendingToKindle || detail.hasActiveProcessing}
              loading={sendingToKindle}
              loadingLabel="Sending..."
            >
              {hasSentToKindle ? "Resend to Kindle" : "Send to Kindle"}
            </AsyncButton>
          ) : null}
          {book.record_type === "manual" && canEditMetadata ? (
            <button
              type="button"
              data-testid="book-edit-hero-button"
              className="ghost-button book-edit-button"
              onClick={actions.onStartEdit}
            >
              Edit Book
            </button>
          ) : null}
          {detail.downloadableAssets.map((asset) => {
            const isDownloading = Boolean(assetLoadingCounts[asset.id]);
            const isHtmlPreviewLocked =
              asset.asset_type === "html" &&
              (Boolean(htmlPreviewLockedByAssetId[asset.id]) || (book && book.can_view_preview_html === false));
            return (
              <AsyncButton
                key={asset.id}
                type="button"
                data-testid={`book-asset-${asset.asset_type}`}
                className="ghost-button asset-link"
                onClick={() => actions.downloadAsset(asset)}
                disabled={isDownloading || isHtmlPreviewLocked}
                loading={isDownloading}
                loadingLabel="Preparing..."
              >
                {isHtmlPreviewLocked
                  ? "Preview Open"
                  : assetLabels[asset.asset_type] ||
                    `Download ${asset.asset_type.toUpperCase()}`}
              </AsyncButton>
            );
          })}
          {canEditMetadata ? (
            <>
              <input
                ref={epubInputRef}
                type="file"
                accept=".epub,application/epub+zip"
                hidden
                onChange={actions.replaceEpub}
              />
              <AsyncButton
                type="button"
                data-testid="book-replace-epub-button"
                className="ghost-button"
                onClick={actions.openEpubPicker}
                disabled={
                  pickingEpub ||
                  replacingEpub ||
                  regenerating ||
                  detail.hasActiveProcessing
                }
                loading={pickingEpub || replacingEpub}
                loadingLabel={pickingEpub ? "Selecting..." : "Uploading..."}
              >
                {detail.epubAsset ? "Replace EPUB" : "Upload EPUB"}
              </AsyncButton>
            </>
          ) : null}
        </div>

        {detail.latestProcessingJob &&
        (detail.hasActiveProcessing || detail.hasFailedProcessing) ? (
          <div
            className={`book-status-note${detail.hasActiveProcessing ? " book-status-note-processing" : ""}${
              detail.hasFailedProcessing ? " book-status-note-error" : ""
            }`}
          >
            <div className="book-status-note-head">
              <span className="fact-label">Processing</span>
              {detail.hasActiveProcessing ? <LoadingSpinner size={14} /> : null}
            </div>
            <strong>{detail.processingHeading}</strong>
            <p>{detail.processingBody}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
