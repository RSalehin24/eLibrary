import { useState, useRef } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import DOMPurify from "dompurify";
import {
  getBookReturnTarget,
  getCurrentRoutePath,
} from "../components/BookRouteLink";
import ConfirmationDialog from "../components/ConfirmationDialog";
import BookDetailSkeleton from "../components/BookDetailSkeleton";
import BookDetailHero from "../features/book-detail/components/BookDetailHero";
import BookMetadataWorkspace from "../features/book-detail/components/BookMetadataWorkspace";
import BookReaderSections from "../features/book-detail/components/BookReaderSections";
import BookTocSummary from "../features/book-detail/components/BookTocSummary";
import PhysicalBookWorkspace from "../features/book-detail/components/PhysicalBookWorkspace";
import { useBookDetailActions } from "../features/book-detail/hooks/useBookDetailActions";
import { useBookDetailData } from "../features/book-detail/hooks/useBookDetailData";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSession } from "../hooks/useSession";
import { useToast } from "../hooks/useToast";
import { getSourceLabel, getContributorNamesByRole } from "../utils/bookPresentation";
import { hasCapability } from "../utils/capabilities";
import { ManualBookComposer } from "../features/manual-books/ManualBookComposer";
import { loadManualBookOptions } from "../features/manual-books/manualBookOptions";
import { emptyManualBookForm } from "../features/manual-books/manualBookFilters";
import { bookDetailFetch } from "../features/book-detail/api";

export default function BookDetailPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useSession();
  const toast = useToast();
  const { slug } = useParams();
  const canEditMetadata = hasCapability(user, "metadata:edit");
  const canViewSourceRecords = hasCapability(user, "source_records:view");
  const currentDetailPath = getCurrentRoutePath(location);
  const returnTarget = getBookReturnTarget(location);
  const detailState = useBookDetailData({
    canEditMetadata,
    location,
    navigate,
    slug,
    toast,
    user,
  });
  usePageTitle(detailState.book?.title || "Book");
  const actions = useBookDetailActions({
    book: detailState.book,
    currentDetailPath,
    detail: detailState.detail,
    editor: detailState.editor,
    fetchBook: detailState.fetchBook,
    htmlPreviewLockedByAssetId: detailState.htmlPreviewLockedByAssetId,
    navigate,
    refreshMetadataCollections: detailState.refreshMetadataCollections,
    replaceBookRoute: detailState.replaceBookRoute,
    returnTarget,
    reviewForm: detailState.reviewForm,
    setBook: detailState.setBook,
    setBookmarks: detailState.setBookmarks,
    setHtmlPreviewLockedByAssetId: detailState.setHtmlPreviewLockedByAssetId,
    setMetadataReviews: detailState.setMetadataReviews,
    setReviewForm: detailState.setReviewForm,
    slug,
    toast,
    user,
  });

  const [composerOpen, setComposerOpen] = useState(false);
  const [composerForm, setComposerForm] = useState(emptyManualBookForm);
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [savingManualBook, setSavingManualBook] = useState(false);
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [contributorOptions, setContributorOptions] = useState([]);
  const [seriesOptions, setSeriesOptions] = useState([]);
  const [publisherOptions, setPublisherOptions] = useState([]);
  const titleInputRef = useRef(null);

  async function loadOptionsForEdit() {
    try {
      setLoadingOptions(true);
      const options = await loadManualBookOptions();
      setCategoryOptions(options.categories);
      setContributorOptions(options.contributors);
      setSeriesOptions(options.series);
      setPublisherOptions(options.publishers);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoadingOptions(false);
    }
  }

  function handleStartEdit() {
    if (!detailState.book) return;
    loadOptionsForEdit();

    let bindingValue = "";
    const rawBinding = (detailState.book.binding || detailState.book.manual_binding || "").toLowerCase().trim().replace(/[\s_-]+/g, "");
    if (rawBinding === "hardcover") {
      bindingValue = "hard_cover";
    } else if (rawBinding === "paperback") {
      bindingValue = "paper_back";
    }

    const priceVal = detailState.book.price !== undefined && detailState.book.price !== null ? detailState.book.price : detailState.book.manual_price;

    setComposerForm({
      title: detailState.book.title || "",
      summary: detailState.book.summary || "",
      writers: getContributorNamesByRole(detailState.book, "author"),
      translators: getContributorNamesByRole(detailState.book, "translator"),
      editors: getContributorNamesByRole(detailState.book, "editor"),
      categories: detailState.book.categories || [],
      series: detailState.book.series || [],
      is_compilation: detailState.book.is_compilation || detailState.book.manual_is_compilation || false,
      binding: bindingValue,
      publisher: detailState.book.publisher || detailState.book.manual_publisher || "",
      price: priceVal ? String(priceVal) : "",
    });
    setComposerOpen(true);
  }

  async function handleUpdateManualBook(event) {
    event.preventDefault();
    try {
      setSavingManualBook(true);
      const contributorsInput = [
        ...composerForm.writers.map(name => ({ name, role: "author" })),
        ...composerForm.translators.map(name => ({ name, role: "translator" })),
        ...composerForm.editors.map(name => ({ name, role: "editor" })),
        ...(composerForm.publisher ? [{ name: composerForm.publisher, role: "publisher" }] : [])
      ];

      const body = {
        title: composerForm.title,
        summary: composerForm.summary,
        contributors: contributorsInput,
        categories: composerForm.categories,
        series: composerForm.series,
        is_compilation: composerForm.is_compilation,
        binding: composerForm.binding,
        publisher: composerForm.publisher,
        price: composerForm.price === "" ? null : composerForm.price,
      };

      const updatedBook = await bookDetailFetch(`/catalog/books/${detailState.book.slug}/metadata/`, {
        method: "PATCH",
        body,
      });

      detailState.setBook(updatedBook);
      setComposerOpen(false);
      toast.success("Book updated successfully.");

      if (updatedBook.slug && updatedBook.slug !== slug) {
        detailState.replaceBookRoute(updatedBook.slug);
      }
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSavingManualBook(false);
    }
  }

  actions.onStartEdit = handleStartEdit;

  if (detailState.loading) {
    return <BookDetailSkeleton />;
  }

  if (detailState.error) {
    return (
      <div className="page-state page-state-error">{detailState.error}</div>
    );
  }

  if (composerOpen) {
    return (
      <div className="book-detail-page page-stack">
        <ManualBookComposer
          categoryOptions={categoryOptions}
          contributorOptions={contributorOptions}
          seriesOptions={seriesOptions}
          publisherOptions={publisherOptions}
          form={composerForm}
          loadingOptions={loadingOptions}
          onClose={() => setComposerOpen(false)}
          onSubmit={handleUpdateManualBook}
          setForm={setComposerForm}
          submitting={savingManualBook}
          titleInputRef={titleInputRef}
          isEditing={true}
        />
      </div>
    );
  }

  const {
    book,
    bookLinkFilters,
    bookmarks,
    detail,
    editor,
    htmlPreviewLockedByAssetId,
    metadataReviews,
    metadataVersions,
    readerAccess,
    readerState,
    reviewForm,
    setEditor,
    setReviewForm,
  } = detailState;

  return (
    <div className="book-detail-page page-stack">
      <BookDetailHero
        actions={actions}
        assetLoadingCounts={actions.assetLoadingCounts}
        book={book}
        bookIdValue={detail.bookIdValue}
        bookLinkFilters={bookLinkFilters}
        canEditMetadata={canEditMetadata}
        deleting={actions.deleting}
        detail={detail}
        epubInputRef={actions.epubInputRef}
        hasKindleEmail={Boolean(user?.kindle_emails?.length)}
        hasSentToKindle={Boolean(book?.has_sent_to_kindle)}
        htmlPreviewLockedByAssetId={htmlPreviewLockedByAssetId}
        launchingReader={actions.launchingReader}
        pickingEpub={actions.pickingEpub}
        primaryContributorGroup={detail.primaryContributorGroup}
        regenerating={actions.regenerating}
        replacingEpub={actions.replacingEpub}
        sendingToKindle={actions.sendingToKindle}
        supportingContributorGroups={detail.supportingContributorGroups}
      />

      {book.record_type === "manual" ? (
        <PhysicalBookWorkspace book={book} />
      ) : (
        <>
          {/* ── Reading notes: shown right after the hero for logged-in users ── */}
          <BookReaderSections
            bookmarks={bookmarks}
            bookSlug={book?.slug || slug}
            deletingBookmarkId={actions.deletingBookmarkId}
            onDeleteBookmark={actions.deleteBookmark}
            progressPercent={detail.progressPercent}
            readerAccess={readerAccess}
            readerState={readerState}
          />

          {canViewSourceRecords && detail.sourceRecords.length ? (
            <section className="detail-card">
              <div className="panel-header">
                <div className="section-title-block">
                  <p className="eyebrow">Source</p>
                  <h2>Source Records</h2>
                </div>
              </div>
              <div className="source-record-list">
                {detail.sourceRecords.map((source, index) => (
                  <article
                    key={`${source.url}-${index}`}
                    className="source-record-card"
                  >
                    <div className="source-record-copy">
                      <span className="fact-label">
                        {source.is_primary ? "Primary" : "Linked"}
                      </span>
                      <strong>{getSourceLabel(source) || "Source page"}</strong>
                      <a
                        className="source-link"
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {source.display_url || source.url}
                      </a>
                    </div>
                    <a
                      className="ghost-button"
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open
                    </a>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {detail.hasFrontMatter ? (
            <section className="detail-card">
              <div className="section-title-block">
                <p className="eyebrow">Extracted</p>
                <h2>Entities and Details</h2>
              </div>
              {detail.extractedEntries.length ? (
                <div className="metadata-list">
                  {detail.extractedEntries.map((entry, index) => (
                    <div
                      key={`${entry.key}-${entry.value}-${index}`}
                      className="metadata-row"
                    >
                      <span className="fact-label">{entry.label}</span>
                      <strong className="metadata-value">{entry.value}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <div
                  className="rich-content-block"
                  dangerouslySetInnerHTML={{
                    __html: DOMPurify.sanitize(book.book_info_html),
                  }}
                />
              )}
            </section>
          ) : null}

          {detail.hasDedication ? (
            <section className="detail-card">
              <div className="section-title-block">
                <p className="eyebrow">Extracted</p>
                <h2>Dedication</h2>
              </div>
              <div
                className="rich-content-block"
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(book.dedication_html),
                }}
              />
            </section>
          ) : null}

          {detail.hasToc ? (
            <section className="detail-card">
              <div className="section-title-block">
                <p className="eyebrow">Structure</p>
                <h2>Table of Contents</h2>
              </div>
              <BookTocSummary toc={book.toc || []} />
            </section>
          ) : null}

          {book.empty_chapters?.length > 0 ? (
            <section className="detail-card">
              <div className="section-title-block">
                <p className="eyebrow">Attention required</p>
                <h2>Chapters without content ({book.empty_chapters.length})</h2>
              </div>
              <p className="detail-description">
                The following chapters are in the table of contents but have no
                content in the generated book. Regenerate the book to retry fetching
                them.
              </p>
              <div className="toc-record-list">
                {book.empty_chapters.map((ch, i) => (
                  <article
                    key={i}
                    className="toc-record-card toc-record-card--empty"
                  >
                    <div className="toc-record-copy">
                      <strong>{ch.title || `Chapter ${i + 1}`}</strong>
                      <div className="inline-pills toc-record-pills">
                        {ch.type ? (
                          <span className="status-pill">{ch.type}</span>
                        ) : null}
                        <span className="status-pill status-needs_review">
                          {ch.has_content === null
                            ? "No content on source"
                            : "Fetch failed"}
                        </span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </>
      )}

      {canEditMetadata && book.record_type !== "manual" ? (
        <BookMetadataWorkspace
          editor={editor}
          metadataReviews={metadataReviews}
          metadataVersions={metadataVersions}
          onCreateMetadataReview={actions.createMetadataReview}
          onSaveMetadata={actions.saveMetadata}
          onSetEditor={setEditor}
          onSetReviewForm={setReviewForm}
          onUpdateMetadataReview={actions.updateMetadataReview}
          reviewForm={reviewForm}
          reviewUpdating={actions.reviewUpdating}
          savingMetadata={actions.savingMetadata}
          savingReview={actions.savingReview}
        />
      ) : null}

      {book.record_type !== "manual" && book.raw_provenance && Object.keys(book.raw_provenance).length ? (
        <section className="detail-card raw-provenance-card">
          <div className="section-title-block">
            <p className="eyebrow">Staff</p>
            <h2>Raw Provenance</h2>
          </div>
          <pre className="json-block raw-provenance-block">
            {JSON.stringify(book.raw_provenance, null, 2)}
          </pre>
        </section>
      ) : null}

      <ConfirmationDialog
        open={actions.deleteDialogOpen}
        title="Delete Book?"
        body={
          book
            ? `Delete "${book.title}"? This will hide it from the catalog.`
            : ""
        }
        confirmLabel="Delete Book"
        loading={actions.deleting}
        onCancel={() => {
          if (!actions.deleting) {
            actions.setDeleteDialogOpen(false);
          }
        }}
        onConfirm={actions.confirmDeleteBook}
      />
    </div>
  );
}
