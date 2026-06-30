import { useState, useEffect } from "react";
import { useToast } from "../../../hooks/useToast";

export default function PhysicalBookWorkspace({ book }) {
  const toast = useToast();

  const [status, setStatus] = useState("unread");
  const [currentPage, setCurrentPage] = useState("");
  const [totalPages, setTotalPages] = useState("");
  const [rating, setRating] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [finishedDate, setFinishedDate] = useState("");
  const [notes, setNotes] = useState("");

  // Load from local storage on mount/slug change
  useEffect(() => {
    const saved = localStorage.getItem(`elibrary_physical_reading_log_${book.slug}`);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setStatus(parsed.status || "unread");
        setCurrentPage(parsed.currentPage || "");
        setTotalPages(parsed.totalPages || "");
        setRating(parsed.rating || 0);
        setStartDate(parsed.startDate || "");
        setFinishedDate(parsed.finishedDate || "");
        setNotes(parsed.notes || "");
      } catch (e) {
        console.error("Failed to parse physical reading log", e);
      }
    } else {
      setStatus("unread");
      setCurrentPage("");
      setTotalPages("");
      setRating(0);
      setStartDate("");
      setFinishedDate("");
      setNotes("");
    }
  }, [book.slug]);

  // Handle status changes (auto-fill page progress and dates)
  const handleStatusChange = (nextStatus) => {
    setStatus(nextStatus);
    const today = new Date().toISOString().split("T")[0];

    if (nextStatus === "finished") {
      if (totalPages) {
        setCurrentPage(totalPages);
      }
      if (!startDate) {
        setStartDate(today);
      }
      setFinishedDate(today);
    } else if (nextStatus === "unread") {
      setCurrentPage("");
      setStartDate("");
      setFinishedDate("");
    } else if (nextStatus === "reading") {
      if (!startDate) {
        setStartDate(today);
      }
      setFinishedDate("");
    }
  };

  // Handle page progress updates
  const handleCurrentPageChange = (val) => {
    const numeric = val === "" ? "" : Math.max(0, parseInt(val, 10) || 0);
    setCurrentPage(numeric);

    if (totalPages && numeric >= parseInt(totalPages, 10)) {
      setStatus("finished");
      if (!finishedDate) {
        setFinishedDate(new Date().toISOString().split("T")[0]);
      }
    } else if (numeric > 0) {
      setStatus("reading");
      setFinishedDate("");
    }
  };

  const handleTotalPagesChange = (val) => {
    const numeric = val === "" ? "" : Math.max(0, parseInt(val, 10) || 0);
    setTotalPages(numeric);
  };

  // Calculate percentage progress
  const progressPercent =
    currentPage && totalPages
      ? Math.min(100, Math.round((parseInt(currentPage, 10) / parseInt(totalPages, 10)) * 100))
      : 0;

  const handleSave = (e) => {
    e.preventDefault();
    const data = {
      status,
      currentPage,
      totalPages,
      rating,
      startDate,
      finishedDate,
      notes,
    };
    localStorage.setItem(`elibrary_physical_reading_log_${book.slug}`, JSON.stringify(data));
    toast.success("Reading log saved successfully.");
  };

  const handleReset = () => {
    if (window.confirm("Are you sure you want to reset your reading log for this book?")) {
      localStorage.removeItem(`elibrary_physical_reading_log_${book.slug}`);
      setStatus("unread");
      setCurrentPage("");
      setTotalPages("");
      setRating(0);
      setStartDate("");
      setFinishedDate("");
      setNotes("");
      toast.success("Reading log reset.");
    }
  };

  return (
    <div className="physical-book-workspace stack-gap">
      <section className="detail-card physical-book-specs-card">
        <div className="section-title-block">
          <p className="eyebrow">Specifications</p>
          <h2>Physical Book Details</h2>
        </div>
        <div className="physical-specs-grid">
          <div className="spec-item">
            <span className="spec-label">Publisher</span>
            <span className="spec-value">{book.publisher || "Not specified"}</span>
          </div>
          <div className="spec-item">
            <span className="spec-label">Binding</span>
            <span className="spec-value">
              {book.binding === "hard_cover"
                ? "Hard Cover"
                : book.binding === "paper_back"
                  ? "Paper Back"
                  : book.binding || "Not specified"}
            </span>
          </div>
          <div className="spec-item">
            <span className="spec-label">Price</span>
            <span className="spec-value">
              {book.price ? `৳ ${parseFloat(book.price).toFixed(2)}` : "Not specified"}
            </span>
          </div>
          <div className="spec-item">
            <span className="spec-label">Compilation</span>
            <span className="spec-value">{book.is_compilation ? "Yes" : "No"}</span>
          </div>
        </div>
      </section>

      <section className="detail-card reading-log-card">
        <div className="section-title-block">
          <p className="eyebrow">Personal</p>
          <h2>My Reading Log</h2>
        </div>
        <form onSubmit={handleSave} className="reading-log-form">
          <div className="reading-log-field">
            <label>Reading Status</label>
            <div className="reading-status-group">
              <button
                type="button"
                className={`reading-status-btn status-unread ${status === "unread" ? "is-active" : ""}`}
                onClick={() => handleStatusChange("unread")}
              >
                Unread
              </button>
              <button
                type="button"
                className={`reading-status-btn status-reading ${status === "reading" ? "is-active" : ""}`}
                onClick={() => handleStatusChange("reading")}
              >
                📖 Reading
              </button>
              <button
                type="button"
                className={`reading-status-btn status-finished ${status === "finished" ? "is-active" : ""}`}
                onClick={() => handleStatusChange("finished")}
              >
                Finished
              </button>
            </div>
          </div>

          <div className="reading-log-grid">
            <div className="reading-log-field">
              <label htmlFor="log-current-page">Current Page</label>
              <input
                id="log-current-page"
                type="number"
                min="0"
                className="reading-log-input"
                value={currentPage}
                onChange={(e) => handleCurrentPageChange(e.target.value)}
                placeholder="e.g. 45"
              />
            </div>
            <div className="reading-log-field">
              <label htmlFor="log-total-pages">Total Pages</label>
              <input
                id="log-total-pages"
                type="number"
                min="1"
                className="reading-log-input"
                value={totalPages}
                onChange={(e) => handleTotalPagesChange(e.target.value)}
                placeholder="e.g. 320"
              />
            </div>
          </div>

          {totalPages ? (
            <div className="progress-slider-wrapper">
              <span className="spec-label">Progress ({progressPercent}%)</span>
              <div className="progress-slider-container">
                <input
                  type="range"
                  min="0"
                  max={totalPages}
                  value={currentPage || 0}
                  onChange={(e) => handleCurrentPageChange(e.target.value)}
                  className="progress-slider"
                />
                <span className="spec-value">
                  {currentPage || 0} / {totalPages} pages
                </span>
              </div>
              <div className="progress-bar-background">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${progressPercent}%` }}
                ></div>
              </div>
            </div>
          ) : null}

          <div className="reading-log-grid">
            <div className="reading-log-field">
              <label htmlFor="log-start-date">Started Date</label>
              <input
                id="log-start-date"
                type="date"
                className="reading-log-input"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="reading-log-field">
              <label htmlFor="log-finish-date">Finished Date</label>
              <input
                id="log-finish-date"
                type="date"
                className="reading-log-input"
                value={finishedDate}
                onChange={(e) => setFinishedDate(e.target.value)}
              />
            </div>
          </div>

          <div className="reading-log-field">
            <label>My Rating</label>
            <div className="rating-stars">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  className={`star-btn ${star <= rating ? "is-filled" : ""}`}
                  onClick={() => setRating(star === rating ? 0 : star)}
                  aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
                >
                  ★
                </button>
              ))}
            </div>
          </div>

          <div className="reading-log-field">
            <label htmlFor="log-notes">Reading Notes</label>
            <textarea
              id="log-notes"
              className="reading-log-textarea"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="What are your thoughts on this book so far?"
            />
          </div>

          <div className="reading-log-actions">
            <button type="submit" className="primary-button">
              Save Progress
            </button>
            <button type="button" className="ghost-button" onClick={handleReset}>
              Reset Log
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
