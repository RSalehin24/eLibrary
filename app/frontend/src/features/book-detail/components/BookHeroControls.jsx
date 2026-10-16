import LoadingSpinner from "../../../components/LoadingSpinner";
import { RefreshIcon, TrashIcon } from "./BookDetailIcons";

export default function BookHeroControls({ actions, book, deleting, detail, regenerating }) {
  return (
<div className="book-hero-controls">
          {book.record_type !== "manual" ? (
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
          ) : null}
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
  );
}
