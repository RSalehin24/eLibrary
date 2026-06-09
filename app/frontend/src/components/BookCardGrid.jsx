import BookCard from "./BookCard";
import BookCardSkeleton from "./BookCardSkeleton";
import { CATALOG_TABLE_PREFETCH_TRIGGER } from "../utils/catalogBooks";

export default function BookCardGrid({
  books,
  hasMore = false,
  observeLoadTrigger = undefined,
  initialLoading = false,
  loadingMore = false,
  refreshing = false,
  initialSkeletonCount = 6,
  incrementalSkeletonCount = 6,
  onRemoveFromMyBooks = null,
  removingBookIds = {},
  onMyBooksToggle = null,
  myBooksBusyIds = {},
  onSendToKindle = null,
  sendingBookKindleIds = {},
  hasKindleEmail = false,
}) {
  const showInitialSkeleton = (initialLoading || refreshing) && !books?.length;
  const showIncrementalSkeleton = loadingMore && books?.length > 0;

  return (
    <section
      className={`book-grid${showInitialSkeleton ? " book-grid-loading" : ""}`}
      aria-busy={initialLoading || loadingMore || refreshing}
    >
      {showInitialSkeleton
        ? Array.from({ length: initialSkeletonCount }, (_, index) => (
            <BookCardSkeleton
              key={`initial-skeleton-${index}`}
              testId={index === 0 ? "book-grid-skeleton" : undefined}
            />
          ))
        : books?.map((book, index) => (
            <BookCard
              key={book.id}
              book={book}
              onRemoveFromMyBooks={onRemoveFromMyBooks}
              onMyBooksToggle={onMyBooksToggle}
              onSendToKindle={onSendToKindle}
              sendingToKindle={Boolean(sendingBookKindleIds[book.id])}
              hasKindleEmail={hasKindleEmail}
              removing={Boolean(
                removingBookIds[book.id] ||
                  removingBookIds[book.slug] ||
                  myBooksBusyIds[book.id]
              )}
              cardRef={
                hasMore &&
                typeof observeLoadTrigger === "function" &&
                index ===
                  Math.max(0, books.length - CATALOG_TABLE_PREFETCH_TRIGGER)
                  ? observeLoadTrigger
                  : undefined
              }
            />
          ))}
      {showIncrementalSkeleton
        ? Array.from({ length: incrementalSkeletonCount }, (_, index) => (
            <BookCardSkeleton
              key={`incremental-skeleton-${index}`}
              testId={index === 0 ? "book-grid-load-more-skeleton" : undefined}
            />
          ))
        : null}
    </section>
  );
}
