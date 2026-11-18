/**
 * BookReaderSections
 *
 * Shows reading stats + four individual note-type cards
 * (Bookmarks / Notes / Annotations / Quotes).
 *
 * Only cards with at least one item are rendered — sections with count 0
 * are hidden entirely.  Each card body has a fixed height and scrolls.
 *
 * Uses the same CSS classes as NotesPage (.notes-item-list, .notes-item, …)
 * so the two surfaces look consistent without duplicating styles.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import LoadingSpinner from "../../../components/LoadingSpinner";
import { fetchMyNotes } from "../../../api/reading";
import { formatBookDateTime } from "../../../utils/bookPresentation";

export default function BookReaderSections({
  bookmarks,
  deletingBookmarkId,
  onDeleteBookmark,
  progressPercent,
  readerAccess,
  readerState,
  bookSlug,
}) {
  const [highlights, setHighlights] = useState([]);
  const [notes, setNotes] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!readerAccess || !bookSlug) {
      setHighlights([]);
      setNotes([]);
      setQuotes([]);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchMyNotes({ book: bookSlug })
      .then((payload) => {
        if (cancelled) return;
        setHighlights(
          Array.isArray(payload?.highlights) ? payload.highlights : [],
        );
        setNotes(Array.isArray(payload?.notes) ? payload.notes : []);
        setQuotes(Array.isArray(payload?.quotes) ? payload.quotes : []);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.message || "Could not load notes.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [bookSlug, readerAccess]);

  const bmCount = bookmarks?.length ?? 0;
  const ntCount = highlights.length; // "highlights" from API = user-facing "Notes"
  const anCount = notes.length;      // "notes" from API     = user-facing "Annotations"
  const qtCount = quotes.length;
  const hasAny = bmCount + ntCount + anCount + qtCount > 0;

  return (
    <section className="book-detail-grid" data-testid="book-reader-sections">
      {/* ── Reading stats ─────────────────────────────────────── */}
      <section className="detail-card">
        <div className="section-title-block">
          <p className="eyebrow">Reader</p>
          <h2>Reading</h2>
        </div>
        {readerAccess ? (
          <div className="reader-stats-grid">
            <article className="book-detail-chip">
              <span className="fact-label">Progress</span>
              <strong>{progressPercent}%</strong>
            </article>
            <article className="book-detail-chip">
              <span className="fact-label">Last location</span>
              <strong className="metadata-value">
                {readerState.last_location || "Not synced"}
              </strong>
            </article>
            <article className="book-detail-chip">
              <span className="fact-label">Last opened</span>
              <strong>
                {readerState.last_opened_at
                  ? formatBookDateTime(readerState.last_opened_at)
                  : "Not synced"}
              </strong>
            </article>
          </div>
        ) : (
          <p className="muted-copy">Syncs after reading.</p>
        )}
      </section>

      {/* ── Note sections (one card each, only if count > 0) ──── */}
      {readerAccess && (
        <>
          {loading ? (
            <section className="detail-card">
              <div className="section-title-block">
                <p className="eyebrow">Reader</p>
                <h2>Notes</h2>
              </div>
              <div className="brs-loading">
                <LoadingSpinner size={20} />
              </div>
            </section>
          ) : error ? (
            <section className="detail-card">
              <div className="section-title-block">
                <p className="eyebrow">Reader</p>
                <h2>Notes</h2>
              </div>
              <p className="muted-copy">{error}</p>
            </section>
          ) : (
            <>
              {bmCount > 0 && (
                <NoteSection title="Bookmarks" icon="🔖" count={bmCount}>
                  <BookmarkList
                    bookmarks={bookmarks}
                    bookSlug={bookSlug}
                    deletingBookmarkId={deletingBookmarkId}
                    onDeleteBookmark={onDeleteBookmark}
                  />
                </NoteSection>
              )}
              {ntCount > 0 && (
                <NoteSection title="Notes" icon="📝" count={ntCount}>
                  <HighlightList items={highlights} bookSlug={bookSlug} />
                </NoteSection>
              )}
              {anCount > 0 && (
                <NoteSection title="Annotations" icon="💬" count={anCount}>
                  <NotesList items={notes} bookSlug={bookSlug} />
                </NoteSection>
              )}
              {qtCount > 0 && (
                <NoteSection title="Quotes" icon="❝" count={qtCount}>
                  <QuoteList items={quotes} bookSlug={bookSlug} />
                </NoteSection>
              )}
              {!hasAny && (
                <section className="detail-card">
                  <div className="section-title-block">
                    <p className="eyebrow">Reader</p>
                    <h2>Notes</h2>
                  </div>
                  <p className="muted-copy">
                    No bookmarks, notes, or quotes yet.
                  </p>
                </section>
              )}
              <div className="brs-manage-row">
                <Link
                  to="/notes"
                  className="notes-action-btn notes-action-btn--primary"
                >
                  Manage all notes →
                </Link>
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}

/* ── Section wrapper ──────────────────────────────────────────── */

function NoteSection({ title, icon, count, children }) {
  return (
    <section className="detail-card detail-card-brs">
      <div className="brs-note-header">
        <p className="eyebrow">Reader</p>
        <h2 className="brs-note-title">
          <span aria-hidden="true">{icon}</span>
          {title}
          <span className="brs-count-pill">{count}</span>
        </h2>
      </div>
      <div className="brs-notes-body">{children}</div>
    </section>
  );
}

/* ── Sub-lists ────────────────────────────────────────────────── */

function BookmarkList({
  bookmarks,
  bookSlug,
  deletingBookmarkId,
  onDeleteBookmark,
}) {
  if (!bookmarks.length) {
    return <p className="muted-copy">No bookmarks yet.</p>;
  }
  return (
    <div className="notes-item-list">
      {bookmarks.map((b) => (
        <BookmarkItem
          key={b.id}
          bookmark={b}
          bookSlug={bookSlug}
          deleting={deletingBookmarkId === b.id}
          onDelete={onDeleteBookmark}
        />
      ))}
    </div>
  );
}

function BookmarkItem({ bookmark: b, bookSlug, deleting, onDelete }) {
  return (
    <article className="notes-item">
      <div className="notes-item-meta">
        {b.chapter_label ? (
          <span className="notes-item-chapter">{b.chapter_label}</span>
        ) : null}
        <span className="notes-item-date">
          {b.created_at ? new Date(b.created_at).toLocaleDateString() : ""}
        </span>
        <span className="notes-item-actions">
          {deleting ? (
            <LoadingSpinner size={12} />
          ) : (
            <button
              type="button"
              data-testid={`bookmark-remove-${b.id}`}
              className="notes-icon-btn notes-icon-btn--danger"
              title="Delete"
              aria-label="Delete bookmark"
              onClick={() => onDelete(b.id)}
            >
              🗑
            </button>
          )}
        </span>
      </div>
      {b.label || b.preview_text ? (
        <p className="notes-item-text">{b.label || b.preview_text}</p>
      ) : null}
      {b.note ? <p className="notes-item-note">{b.note}</p> : null}
      {bookSlug ? (
        <div className="notes-item-footer">
          <Link to={`/books/${bookSlug}/read`} className="notes-open-link">
            Open in reader →
          </Link>
        </div>
      ) : null}
    </article>
  );
}

function HighlightList({ items, bookSlug }) {
  if (!items.length) return <p className="muted-copy">No notes yet.</p>;
  return (
    <ul className="notes-item-list">
      {items.map((h) => (
        <li key={h.id}>
          <article className="notes-item">
            <div className="notes-item-meta">
              {h.chapter_label ? (
                <span className="notes-item-chapter">{h.chapter_label}</span>
              ) : null}
              <span className="notes-item-date">
                {h.created_at
                  ? new Date(h.created_at).toLocaleDateString()
                  : ""}
              </span>
            </div>
            {h.text ? (
              <p
                className={`notes-item-text${h.color === "underline" ? " notes-item-text--underline" : ""}`}
              >
                {h.text}
              </p>
            ) : null}
            {bookSlug ? (
              <div className="notes-item-footer">
                <Link
                  to={`/books/${bookSlug}/read`}
                  className="notes-open-link"
                >
                  Open in reader →
                </Link>
              </div>
            ) : null}
          </article>
        </li>
      ))}
    </ul>
  );
}

function NotesList({ items, bookSlug }) {
  if (!items.length)
    return (
      <p className="muted-copy">
        No annotations yet. Select text and use 💬.
      </p>
    );
  return (
    <ul className="notes-item-list">
      {items.map((h) => (
        <li key={h.id}>
          <article className="notes-item">
            <div className="notes-item-meta">
              {h.chapter_label ? (
                <span className="notes-item-chapter">{h.chapter_label}</span>
              ) : null}
              <span className="notes-item-date">
                {h.created_at
                  ? new Date(h.created_at).toLocaleDateString()
                  : ""}
              </span>
            </div>
            {h.text ? (
              <p
                className={`notes-item-text${h.color === "underline" ? " notes-item-text--underline" : ""}`}
              >
                {h.text}
              </p>
            ) : null}
            {h.note ? (
              <p className="notes-item-note">
                <span className="notes-comment-glyph" aria-hidden="true">
                  💬
                </span>
                {h.note}
              </p>
            ) : null}
            {bookSlug ? (
              <div className="notes-item-footer">
                <Link
                  to={`/books/${bookSlug}/read`}
                  className="notes-open-link"
                >
                  Open in reader →
                </Link>
              </div>
            ) : null}
          </article>
        </li>
      ))}
    </ul>
  );
}

function QuoteList({ items, bookSlug }) {
  if (!items.length)
    return (
      <p className="muted-copy">No quotes yet. Select text and use ❝.</p>
    );
  return (
    <ul className="notes-item-list">
      {items.map((q) => (
        <li key={q.id}>
          <article className="notes-item">
            <div className="notes-item-meta">
              {q.chapter_label ? (
                <span className="notes-item-chapter">{q.chapter_label}</span>
              ) : null}
              <span className="notes-item-date">
                {q.created_at
                  ? new Date(q.created_at).toLocaleDateString()
                  : ""}
              </span>
            </div>
            {q.text ? (
              <p className="notes-item-text notes-item-text--quote">
                <span className="notes-quote-glyph" aria-hidden="true">
                  ❝
                </span>
                {q.text}
              </p>
            ) : null}
            {q.note ? <p className="notes-item-note">{q.note}</p> : null}
            {bookSlug ? (
              <div className="notes-item-footer">
                <Link
                  to={`/books/${bookSlug}/read`}
                  className="notes-open-link"
                >
                  Open in reader →
                </Link>
              </div>
            ) : null}
          </article>
        </li>
      ))}
    </ul>
  );
}
