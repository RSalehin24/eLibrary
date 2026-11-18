import LoadingSpinner from "../../components/LoadingSpinner";

export function SavedFilterStrip({
  onApply,
  onDelete,
  savedFilterAction,
  savedFilters
}) {
  if (!savedFilters.length) {
    return null;
  }

  return (
    <section className="catalog-saved-strip" aria-label="Saved filters">
      {savedFilters.map((filter) => (
        <div key={filter.id} className="saved-filter-chip">
          <button
            type="button"
            className="saved-filter-apply"
            onClick={() => onApply(filter)}
            disabled={Boolean(savedFilterAction)}
          >
            {savedFilterAction === `apply:${filter.id}` ? (
              <span className="button-label">
                <LoadingSpinner size={12} /> Applying...
              </span>
            ) : (
              filter.name
            )}
          </button>
          <button
            type="button"
            className="saved-filter-delete"
            onClick={() => onDelete(filter.id)}
            aria-label={`Delete ${filter.name}`}
            disabled={Boolean(savedFilterAction)}
          >
            {savedFilterAction === `delete:${filter.id}` ? "…" : "×"}
          </button>
        </div>
      ))}
    </section>
  );
}
