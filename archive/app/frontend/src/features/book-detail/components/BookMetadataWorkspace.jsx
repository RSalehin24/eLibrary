import LoadingSpinner from "../../../components/LoadingSpinner";
import {
  formatBookDateTime,
  getStatusMeta,
} from "../../../utils/bookPresentation";

export default function BookMetadataWorkspace({
  editor,
  metadataReviews,
  metadataVersions,
  onCreateMetadataReview,
  onSaveMetadata,
  onSetEditor,
  onSetReviewForm,
  onUpdateMetadataReview,
  reviewForm,
  reviewUpdating,
  savingMetadata,
  savingReview,
}) {
  return (
    <section className="detail-card" data-testid="book-metadata-workspace">
      <div className="section-title-block">
        <p className="eyebrow">Editorial</p>
        <h2>Metadata Workspace</h2>
      </div>

      <div className="book-admin-grid">
        <form className="stack-form metadata-form" onSubmit={onSaveMetadata}>
          <div className="metadata-form-grid">
            <label className="field-span-full">
              <span>Title</span>
              <input
                value={editor.title}
                onChange={(event) =>
                  onSetEditor({ ...editor, title: event.target.value })
                }
              />
            </label>
            <label className="field-span-full">
              <span>Summary</span>
              <textarea
                rows="4"
                value={editor.summary}
                onChange={(event) =>
                  onSetEditor({ ...editor, summary: event.target.value })
                }
              />
            </label>
            <label className="field-span-full">
              <span>Contributors</span>
              <textarea
                rows="5"
                value={editor.contributors}
                onChange={(event) =>
                  onSetEditor({ ...editor, contributors: event.target.value })
                }
                placeholder="Name|author"
              />
            </label>
            <label>
              <span>Series</span>
              <input
                value={editor.series}
                onChange={(event) =>
                  onSetEditor({ ...editor, series: event.target.value })
                }
              />
            </label>
            <label>
              <span>Categories</span>
              <input
                value={editor.categories}
                onChange={(event) =>
                  onSetEditor({ ...editor, categories: event.target.value })
                }
              />
            </label>
            <label className="field-span-full">
              <span>Edit note</span>
              <input
                value={editor.notes}
                onChange={(event) =>
                  onSetEditor({ ...editor, notes: event.target.value })
                }
              />
            </label>
          </div>
          <button
            type="submit"
            className="primary-button"
            disabled={savingMetadata}
          >
            <span className="button-label">
              {savingMetadata ? <LoadingSpinner size={16} /> : null}
              {savingMetadata ? "Saving..." : "Save metadata"}
            </span>
          </button>
        </form>

        <section className="stack-form editorial-panel">
          <form className="stack-form" onSubmit={onCreateMetadataReview}>
            <div className="section-title-block">
              <h3>Review</h3>
            </div>
            <label>
              <span>Review state</span>
              <select
                value={reviewForm.state}
                onChange={(event) =>
                  onSetReviewForm({
                    ...reviewForm,
                    state: event.target.value,
                  })
                }
              >
                <option value="pending">Awaiting review</option>
                <option value="needs_review">Needs review</option>
                <option value="approved">Reviewed</option>
                <option value="rejected">Needs correction</option>
              </select>
            </label>
            <label>
              <span>Notes</span>
              <input
                value={reviewForm.notes}
                onChange={(event) =>
                  onSetReviewForm({
                    ...reviewForm,
                    notes: event.target.value,
                  })
                }
              />
            </label>
            <button
              type="submit"
              className="ghost-button"
              disabled={savingReview}
            >
              <span className="button-label">
                {savingReview ? <LoadingSpinner size={16} /> : null}
                {savingReview ? "Saving..." : "Save review"}
              </span>
            </button>
          </form>
        </section>

        <section className="stack-form editorial-panel">
          <div className="section-title-block">
            <h3>Metadata History</h3>
          </div>
          <div className="queue-list">
            {metadataVersions.length ? (
              metadataVersions.map((version) => (
                <article key={version.id} className="queue-card">
                  <strong>{version.source}</strong>
                  <p>{version.notes || "No notes"}</p>
                  <p>{formatBookDateTime(version.created_at)}</p>
                </article>
              ))
            ) : (
              <p className="muted-copy">No history yet.</p>
            )}
          </div>
        </section>

        <section className="stack-form editorial-panel">
          <div className="section-title-block">
            <h3>Review Log</h3>
          </div>
          <div className="queue-list">
            {metadataReviews.length ? (
              metadataReviews.map((review) => (
                <article key={review.id} className="queue-card">
                  <strong>{getStatusMeta(review.state).label}</strong>
                  <p>{review.notes || "No notes"}</p>
                  <p>
                    {review.requested_by_email || "Unknown"}
                    {review.updated_at
                      ? ` · ${formatBookDateTime(review.updated_at)}`
                      : ""}
                  </p>
                  <div className="inline-pills">
                    <button
                      type="button"
                      className="primary-button"
                      onClick={() =>
                        onUpdateMetadataReview(review.id, "approved")
                      }
                      disabled={Boolean(reviewUpdating.id)}
                    >
                      <span className="button-label">
                        {reviewUpdating.id === review.id &&
                        reviewUpdating.state === "approved" ? (
                          <LoadingSpinner size={14} />
                        ) : null}
                        {reviewUpdating.id === review.id &&
                        reviewUpdating.state === "approved"
                          ? "Approving..."
                          : "Approve"}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="ghost-button"
                      onClick={() =>
                        onUpdateMetadataReview(review.id, "rejected")
                      }
                      disabled={Boolean(reviewUpdating.id)}
                    >
                      <span className="button-label">
                        {reviewUpdating.id === review.id &&
                        reviewUpdating.state === "rejected" ? (
                          <LoadingSpinner size={14} />
                        ) : null}
                        {reviewUpdating.id === review.id &&
                        reviewUpdating.state === "rejected"
                          ? "Rejecting..."
                          : "Reject"}
                      </span>
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <p className="muted-copy">No reviews yet.</p>
            )}
          </div>
        </section>
      </div>
    </section>
  );
}
