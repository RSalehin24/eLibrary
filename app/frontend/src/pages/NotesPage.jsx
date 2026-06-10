import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useId,
} from "react";
import { Link } from "react-router-dom";
import ConfirmationDialog from "../components/ConfirmationDialog";
import PageLoader from "../components/PageLoader";
import {
  deleteBookmark,
  deleteHighlight,
  fetchMyNotes,
  updateHighlight,
} from "../api/reading";
import { useDialogA11y } from "../hooks/useDialogA11y";
import { usePageTitle } from "../hooks/usePageTitle";
import { useToast } from "../hooks/useToast";

// Must match HIGHLIGHT_COLORS in highlight-methods.js
const SWATCHES = [
  { value: "green", fill: "#a5d6a7", label: "Green" },
  { value: "yellow", fill: "#ffeb3b", label: "Yellow" },
  { value: "blue", fill: "#90caf9", label: "Blue" },
  { value: "pink", fill: "#f48fb1", label: "Pink" },
];
const ALL_SWATCHES = [
  ...SWATCHES,
  { value: "underline", fill: "none", label: "Underline" },
];

const TAB_DEFS = [
  { id: "bookmarks", label: "Bookmarks", kindParam: "bookmarks" },
  { id: "highlights", label: "Highlights", kindParam: "highlights" },
  { id: "notes", label: "Notes", kindParam: "notes" },
  { id: "quotes", label: "Quotes", kindParam: "quotes" },
];

const EMPTY_HINTS = {
  bookmarks: "No bookmarks saved yet.",
  highlights: "No highlights yet. Select text in the reader to add one.",
  notes: "No notes yet. Select text in the reader and use the 💬 button.",
  quotes: "No quotes yet. Select text in the reader and use the ❝ button.",
};

function groupByBook(items) {
  const map = new Map();
  for (const item of items) {
    const slug = item.book_slug || String(item.book ?? "");
    if (!map.has(slug)) {
      map.set(slug, {
        slug,
        title: item.book_title || slug || "Untitled book",
        items: [],
      });
    }
    map.get(slug).items.push(item);
  }
  for (const g of map.values()) {
    g.items.sort((a, b) =>
      (b.created_at || "").localeCompare(a.created_at || ""),
    );
  }
  return [...map.values()].sort((a, b) => a.title.localeCompare(b.title));
}

export default function NotesPage() {
  const toast = useToast();
  usePageTitle("My Notes");
  const [activeTab, setActiveTab] = useState("bookmarks");
  const [loading, setLoading] = useState(true);
  const [loadedTabs, setLoadedTabs] = useState(new Set());
  const [data, setData] = useState({
    bookmarks: [],
    highlights: [],
    notes: [],
    quotes: [],
  });
  const [counts, setCounts] = useState({
    bookmarks: 0,
    highlights: 0,
    notes: 0,
    quotes: 0,
  });
  const [query, setQuery] = useState("");
  const [colorFilter, setColorFilter] = useState("");
  const [editModal, setEditModal] = useState(null); // { item, note } or null
  const [deleteTarget, setDeleteTarget] = useState(null); // { item, tab } or null
  const [deleting, setDeleting] = useState(false);
  const searchRef = useRef(null);
  const searchTimer = useRef(null);

  const loadTab = useCallback(
    async (tab, overrides = {}) => {
      setLoading(true);
      const tabDef = TAB_DEFS.find((t) => t.id === tab);
      if (!tabDef) return;
      const q = overrides.query ?? query;
      const color = overrides.color ?? colorFilter;
      const colorable = tab === "highlights" || tab === "notes";
      try {
        const payload = await fetchMyNotes({
          kind: tabDef.kindParam,
          color: colorable ? color || undefined : undefined,
          query: q || undefined,
        });
        const items = payload[tab] || [];
        setData((prev) => ({ ...prev, [tab]: items }));
        setCounts((prev) => ({ ...prev, [tab]: items.length }));
        setLoadedTabs((prev) => new Set([...prev, tab]));
      } catch (err) {
        toast.error(err?.message || "Failed to load notes.");
      } finally {
        setLoading(false);
      }
    },
    [query, colorFilter, toast],
  );

  // On mount: load active tab, background-fetch counts for the others
  useEffect(() => {
    loadTab(activeTab);
    for (const def of TAB_DEFS) {
      if (def.id === activeTab) continue;
      fetchMyNotes({ kind: def.kindParam })
        .then((payload) => {
          const items = payload[def.id] || [];
          setCounts((prev) => ({ ...prev, [def.id]: items.length }));
        })
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!loadedTabs.has(activeTab) || query || colorFilter) {
      loadTab(activeTab);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  function handleTabChange(id) {
    setActiveTab(id);
    if (id !== "highlights" && id !== "notes") setColorFilter("");
  }

  function handleSearch(value) {
    setQuery(value);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(
      () => loadTab(activeTab, { query: value }),
      320,
    );
  }

  function handleColorFilter(value) {
    setColorFilter(value);
    loadTab(activeTab, { color: value });
  }

  async function handleDelete(item) {
    setDeleteTarget({ item, tab: activeTab });
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    const { item, tab } = deleteTarget;
    setDeleting(true);
    try {
      if (tab === "bookmarks") {
        await deleteBookmark(item.id);
      } else {
        await deleteHighlight(item.id);
      }
      setData((prev) => ({
        ...prev,
        [tab]: (prev[tab] || []).filter((it) => it.id !== item.id),
      }));
      setCounts((prev) => ({
        ...prev,
        [tab]: Math.max(0, (prev[tab] || 1) - 1),
      }));
      toast.success("Deleted.");
      setDeleteTarget(null);
    } catch (err) {
      toast.error(err?.message || "Failed to delete.");
    } finally {
      setDeleting(false);
    }
  }

  async function handleColorUpdate(item, color) {
    if (item.color === color) return; // same color — skip
    try {
      const updated = await updateHighlight(item.id, { color });
      setData((prev) => ({
        ...prev,
        [activeTab]: (prev[activeTab] || []).map((h) =>
          h.id === item.id ? updated : h,
        ),
      }));
    } catch (err) {
      toast.error(err?.message || "Failed to update color.");
    }
  }

  function handleNoteEdit(item) {
    setEditModal({ item, note: item.note || "" });
  }

  async function handleNoteEditSave(item, note) {
    setEditModal(null);
    if (note === item.note) return;
    try {
      const updated = await updateHighlight(item.id, { note });
      setData((prev) => ({
        ...prev,
        [activeTab]: (prev[activeTab] || []).map((h) =>
          h.id === item.id ? updated : h,
        ),
      }));
    } catch (err) {
      toast.error(err?.message || "Failed to update note.");
    }
  }

  const items = data[activeTab] || [];
  const groups = useMemo(() => groupByBook(items), [items]);
  const [selectedBook, setSelectedBook] = useState(null);
  const hasSearch = query.trim().length > 0;
  const showColorFilter = activeTab === "highlights" || activeTab === "notes";

  const selectedGroup = useMemo(() => {
    if (!selectedBook) return groups.length === 1 ? groups[0] : null;
    return groups.find((g) => g.slug === selectedBook) || null;
  }, [selectedBook, groups]);

  return (
    <div className="catalog-page catalog-page-notes page-stack">
      {/* ── Header ── */}
      <header className="catalog-page-header notes-page-header">
        <div className="notes-header-row">
          <h1>My Notes</h1>
          <div className="notes-header-search">
            <input
              ref={searchRef}
              type="search"
              className="notes-input notes-header-search-input"
              placeholder="Search in this tab…"
              value={query}
              onChange={(e) => handleSearch(e.target.value)}
              aria-label="Search notes"
            />
            {showColorFilter ? (
              <div className="notes-color-filter-wrapper">
                <span className="notes-color-filter-icon" aria-hidden="true">
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                  >
                    <path d="M1 2.5A.5.5 0 0 1 1.5 2h13a.5.5 0 0 1 .37.83L10 8.67V13.5a.5.5 0 0 1-.22.41l-3 2A.5.5 0 0 1 6 15.5V8.67L1.13 3.33A.5.5 0 0 1 1 2.5z" />
                  </svg>
                </span>
                <select
                  className="notes-select notes-header-color-select"
                  value={colorFilter}
                  onChange={(e) => handleColorFilter(e.target.value)}
                  aria-label="Filter by color"
                >
                  <option value="">All colors</option>
                  {ALL_SWATCHES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
          </div>
        </div>

        {/* ── Tabs ── */}
        <div className="notes-tabs-row">
          <nav className="notes-tabs" role="tablist" aria-label="Notes views">
            {TAB_DEFS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                className={`notes-tab${activeTab === tab.id ? " is-active" : ""}`}
                onClick={() => handleTabChange(tab.id)}
              >
                {tab.label}
                <span className="notes-tab-count" aria-hidden="true">
                  {counts[tab.id]}
                </span>
              </button>
            ))}
          </nav>
          {!loading && groups.length > 0 && (
            <p className="notes-result-count" aria-live="polite">
              {items.length === 1 ? "1 result" : `${items.length} results`}
              {hasSearch ? ` for "${query.trim()}"` : ""}
            </p>
          )}
        </div>
      </header>

      <section>
        {/* ── Note edit modal ── */}
        {editModal ? (
          <NoteEditModal
            item={editModal.item}
            initialNote={editModal.note}
            onSave={(note) => handleNoteEditSave(editModal.item, note)}
            onClose={() => setEditModal(null)}
          />
        ) : null}

        <ConfirmationDialog
          open={Boolean(deleteTarget)}
          title={
            deleteTarget?.tab === "bookmarks"
              ? "Delete bookmark?"
              : "Delete entry?"
          }
          body={
            deleteTarget?.tab === "bookmarks"
              ? "This bookmark will be removed permanently."
              : "This entry will be removed permanently. Any note attached to it will also be deleted."
          }
          confirmLabel="Delete"
          cancelLabel="Cancel"
          onConfirm={confirmDelete}
          onCancel={() => (deleting ? null : setDeleteTarget(null))}
          loading={deleting}
        />

        {/* ── Content ── */}
        {loading ? (
          <PageLoader label="Loading notes" />
        ) : groups.length === 0 ? (
          <p className="notes-empty">{EMPTY_HINTS[activeTab]}</p>
        ) : (
          <div className="notes-two-col">
            {/* ── Left: Books list ── */}
            <aside className="notes-books-sidebar">
              <ul className="notes-books-list">
                {groups.map((group) => {
                  const isActive =
                    selectedGroup && selectedGroup.slug === group.slug;
                  const noun =
                    activeTab === "bookmarks"
                      ? "bookmark"
                      : activeTab === "quotes"
                        ? "quote"
                        : activeTab === "notes"
                          ? "note"
                          : "highlight";
                  return (
                    <li key={group.slug}>
                      <button
                        type="button"
                        className={`notes-books-item${isActive ? " is-active" : ""}`}
                        onClick={() => setSelectedBook(group.slug)}
                      >
                        <span className="notes-books-item-title">
                          {group.slug ? (
                            <Link
                              to={`/books/${group.slug}`}
                              className="notes-books-item-link"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {group.title}
                            </Link>
                          ) : (
                            group.title
                          )}
                        </span>
                        <span className="notes-books-item-count">
                          {group.items.length} {noun}
                          {group.items.length === 1 ? "" : "s"}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </aside>

            {/* ── Right: Notes for selected book ── */}
            <div className="notes-detail-panel">
              {selectedGroup ? (
                <BookGroup
                  group={selectedGroup}
                  tab={activeTab}
                  defaultOpen={true}
                  onDelete={handleDelete}
                  onColorChange={handleColorUpdate}
                  onNoteEdit={handleNoteEdit}
                />
              ) : (
                <p className="notes-empty">
                  Select a book from the left to view its notes.
                </p>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

// ── BookGroup ─────────────────────────────────────────────────────────────────

function BookGroup({ group, tab, defaultOpen = false, ...handlers }) {
  const [open, setOpen] = useState(defaultOpen);
  const noun =
    tab === "bookmarks"
      ? "bookmark"
      : tab === "quotes"
        ? "quote"
        : tab === "notes"
          ? "note"
          : "highlight";
  const count = group.items.length;

  return (
    <section className="notes-book-group" aria-label={group.title}>
      <button
        type="button"
        className="notes-book-group-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="notes-book-group-chevron" aria-hidden="true">
          {open ? "▾" : "▸"}
        </span>
        <h2 className="notes-book-group-title">
          {group.slug ? (
            <Link
              to={`/books/${group.slug}`}
              className="notes-book-group-link"
              onClick={(e) => e.stopPropagation()}
            >
              {group.title}
            </Link>
          ) : (
            group.title
          )}
        </h2>
        <span className="notes-book-group-meta">
          {count} {noun}
          {count === 1 ? "" : "s"}
        </span>
      </button>

      {open ? (
        <ul className="notes-item-list">
          {group.items.map((item) => (
            <li key={item.id}>
              <ItemRow item={item} tab={tab} {...handlers} />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

// ── ItemRow ───────────────────────────────────────────────────────────────────

function ColorDot({ swatch, current, onChange }) {
  const isUnderline = swatch.value === "underline";
  const isActive = current === swatch.value;
  return (
    <button
      type="button"
      title={swatch.label}
      aria-label={`Change color to ${swatch.label}`}
      aria-pressed={isActive}
      className={`notes-color-dot${isActive ? " is-active" : ""}${isUnderline ? " is-underline" : ""}`}
      style={isUnderline ? {} : { "--dot-fill": swatch.fill }}
      onClick={() => onChange(swatch.value)}
    />
  );
}

function ItemRow({ item, tab, onDelete, onColorChange, onNoteEdit }) {
  const isBookmark = tab === "bookmarks";
  const isNote = tab === "notes";
  const isQuote = tab === "quotes";
  const isColorable = tab === "highlights" || tab === "notes";
  const isUnderline = item.color === "underline";

  const text =
    item.text ||
    item.label ||
    item.preview_text ||
    (isBookmark ? "(bookmark)" : "");

  return (
    <article className="notes-item">
      {/* ── Meta row: chapter + date ── */}
      <div className="notes-item-meta">
        {item.chapter_label ? (
          <span className="notes-item-chapter">{item.chapter_label}</span>
        ) : null}
        <span className="notes-item-date">
          {item.created_at
            ? new Date(item.created_at).toLocaleDateString()
            : ""}
        </span>
      </div>

      {/* ── Text block + action buttons immediately below it ── */}
      <div className="notes-item-text-wrap">
        {text ? (
          <p
            className={[
              "notes-item-text",
              isQuote ? "notes-item-text--quote" : "",
              isUnderline ? "notes-item-text--underline" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {isQuote ? (
              <>
                <span className="notes-quote-glyph" aria-hidden="true">
                  ❝
                </span>
                {text}
                <span
                  className="notes-quote-glyph notes-quote-glyph--close"
                  aria-hidden="true"
                >
                  ❞
                </span>
              </>
            ) : (
              text
            )}
          </p>
        ) : null}

        {/* Buttons right-aligned, immediately under text */}
        <div className="notes-item-actions">
          {isNote ? (
            <button
              type="button"
              className="notes-icon-btn"
              title="Edit comment"
              aria-label="Edit comment"
              onClick={() => onNoteEdit(item)}
            >
              ✏️
            </button>
          ) : null}
          <button
            type="button"
            className="notes-icon-btn--danger"
            title="Delete"
            aria-label="Delete"
            onClick={() => onDelete(item)}
          >
            <svg
              viewBox="0 0 24 24"
              width="28"
              height="28"
              aria-hidden="true"
              focusable="false"
            >
              <path
                d="M9 3.75h6a1 1 0 0 1 1 1V6h3a.75.75 0 0 1 0 1.5h-1.1l-.79 10.28A2.5 2.5 0 0 1 14.62 20H9.38a2.5 2.5 0 0 1-2.49-2.22L6.1 7.5H5a.75.75 0 0 1 0-1.5h3V4.75a1 1 0 0 1 1-1Zm5.5 2.25v-.75h-5V6h5Zm-6.9 1.5.78 10.17a1 1 0 0 0 1 .83h5.24a1 1 0 0 0 1-.83l.78-10.17Zm2.4 2.25c.41 0 .75.34.75.75v4.5a.75.75 0 0 1-1.5 0v-4.5c0-.41.34-.75.75-.75Zm4 0c.41 0 .75.34.75.75v4.5a.75.75 0 0 1-1.5 0v-4.5c0-.41.34-.75.75-.75Z"
                fill="currentColor"
              ></path>
            </svg>
          </button>
        </div>
      </div>

      {/* ── Comment body (notes tab) ── */}
      {item.note ? (
        <p className="notes-item-note">
          <span className="notes-comment-glyph" aria-hidden="true">
            💬
          </span>
          {item.note}
        </p>
      ) : null}

      {/* ── Color swatches (highlights + notes) ── */}
      {isColorable ? (
        <div className="notes-color-row" role="group" aria-label="Change color">
          {ALL_SWATCHES.map((sw) => (
            <ColorDot
              key={sw.value}
              swatch={sw}
              current={item.color}
              onChange={(c) => onColorChange(item, c)}
            />
          ))}
        </div>
      ) : null}

      {/* ── Open in reader ── */}
      {item.book_slug ? (
        <div className="notes-item-footer">
          <Link
            to={`/books/${item.book_slug}/read`}
            className="notes-open-link"
          >
            Open in reader →
          </Link>
        </div>
      ) : null}
    </article>
  );
}

// ── Note edit modal ───────────────────────────────────────────────────────────

function NoteEditModal({ item, initialNote, onSave, onClose }) {
  const [note, setNote] = useState(initialNote);
  const textareaId = useId();
  const dialogRef = useDialogA11y(true, { onClose });

  function handleKeyDown(e) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) onSave(note.trim());
  }

  function handleBackdropMouseDown(e) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div
      className="note-modal-backdrop"
      role="presentation"
      onMouseDown={handleBackdropMouseDown}
    >
      <div
        ref={dialogRef}
        className="note-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="note-modal-title"
      >
        <h2 id="note-modal-title" className="note-modal-title">
          Edit comment
        </h2>
        {item.text ? <p className="note-modal-preview">{item.text}</p> : null}
        <label htmlFor={textareaId} className="note-modal-label">
          Comment
        </label>
        <textarea
          id={textareaId}
          className="note-modal-textarea"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={4}
          placeholder="Write your comment…"
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
        />
        <p className="note-modal-hint">Ctrl+Enter to save · Esc to cancel</p>
        <div className="note-modal-footer">
          <button
            type="button"
            className="note-modal-btn note-modal-btn--ghost"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="note-modal-btn note-modal-btn--primary"
            onClick={() => onSave(note.trim())}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
