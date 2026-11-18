import LoadingSpinner from "../../../components/LoadingSpinner";

export default function AccessGrantEditorCard({
  currentUserId,
  filteredTargetOptions,
  grantForm,
  managedUsers,
  onSetGrantForm,
  onSetTargetSearch,
  onSubmit,
  onSwitchTargetType,
  onToggleGrantScope,
  onToggleGrantTarget,
  scopedScopes,
  submittingGrant,
  targetSearch,
}) {
  return (
    <section className="detail-card" data-testid="access-grant-editor">
      <h2>Access Control</h2>
      <form className="stack-form" onSubmit={onSubmit} data-testid="access-grant-form">
        <fieldset className="form-fieldset-reset" disabled={submittingGrant}>
          <div className="detail-facts">
            <label>
              <span className="fact-label">User</span>
              <select
                value={grantForm.user}
                onChange={(event) =>
                  onSetGrantForm({ ...grantForm, user: event.target.value })
                }
              >
                <option value="">Select user</option>
                {managedUsers
                  .filter((entry) => `${entry.id}` !== `${currentUserId}`)
                  .map((entry) => (
                    <option key={entry.id} value={entry.id}>
                      {entry.full_name || entry.email}
                    </option>
                  ))}
              </select>
            </label>
          </div>

          <div className="settings-list">
            <span className="fact-label">Permission</span>
            {scopedScopes.length ? (
              <div className="scope-grid">
                {scopedScopes.map((scope) => (
                  <label key={scope.value} className="scope-card">
                    <input
                      type="checkbox"
                      checked={grantForm.scopes.includes(scope.value)}
                      onChange={() => onToggleGrantScope(scope.value)}
                    />
                    <span>{scope.label}</span>
                  </label>
                ))}
              </div>
            ) : (
              <p className="muted-copy">No scoped permissions are available.</p>
            )}
          </div>

          <div className="settings-list">
            <span className="fact-label">Applies To</span>
            <div className="inline-pills">
              <button
                type="button"
                className={
                  grantForm.targetType === "book"
                    ? "primary-button"
                    : "ghost-button"
                }
                onClick={() => onSwitchTargetType("book")}
              >
                Books
              </button>
              <button
                type="button"
                className={
                  grantForm.targetType === "category"
                    ? "primary-button"
                    : "ghost-button"
                }
                onClick={() => onSwitchTargetType("category")}
              >
                Categories
              </button>
              <button
                type="button"
                className={
                  grantForm.targetType === "writer"
                    ? "primary-button"
                    : "ghost-button"
                }
                onClick={() => onSwitchTargetType("writer")}
              >
                Writers
              </button>
            </div>
            <input
              type="search"
              value={targetSearch}
              onChange={(event) => onSetTargetSearch(event.target.value)}
              onInput={(event) => {
                if (!String(event.target?.value || "").trim()) {
                  onSetTargetSearch("");
                }
              }}
              placeholder={`Search ${grantForm.targetType}s`}
            />
            {filteredTargetOptions.length ? (
              <div className="selection-list">
                {filteredTargetOptions.map((entry) => (
                  <label key={entry.id} className="scope-card">
                    <input
                      type="checkbox"
                      checked={grantForm.targetIds.includes(entry.id)}
                      onChange={() => onToggleGrantTarget(entry.id)}
                    />
                    <span>{entry.label}</span>
                  </label>
                ))}
              </div>
            ) : (
              <p className="muted-copy">No matches found.</p>
            )}
          </div>

          <div className="inline-pills">
            <button type="submit" className="primary-button">
              <span className="button-label">
                {submittingGrant ? <LoadingSpinner size={14} /> : null}
                {submittingGrant ? "Saving..." : "Save Access"}
              </span>
            </button>
          </div>
        </fieldset>
      </form>
    </section>
  );
}
