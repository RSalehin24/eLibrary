export default function AccessGrantRulesCard({
  currentUserId,
  deletingGrantId,
  onDeleteGrant,
  scopedGrants,
  scopeLabelMap,
}) {
  return (
    <section className="detail-card" data-testid="access-rules-section">
      <h2>Current Rules</h2>
      {scopedGrants.length ? (
        <div className="table-shell">
          <table className="simple-table" data-testid="access-rules-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Permission</th>
                <th>Scope</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {scopedGrants.map((grant) => (
                <tr key={grant.id}>
                  <td>{grant.user_email}</td>
                  <td>{scopeLabelMap.get(grant.scope) || grant.scope}</td>
                  <td>{grant.target_label}</td>
                  <td>
                    <div className="table-actions">
                      {`${grant.user}` === `${currentUserId}` ? (
                        <span className="table-note">Locked</span>
                      ) : (
                        <button
                          type="button"
                          className="ghost-button"
                          onClick={() => onDeleteGrant(grant)}
                          disabled={Boolean(deletingGrantId)}
                        >
                          {deletingGrantId === grant.id
                            ? "Deleting..."
                            : "Delete"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted-copy">No scoped access rules yet.</p>
      )}
    </section>
  );
}
