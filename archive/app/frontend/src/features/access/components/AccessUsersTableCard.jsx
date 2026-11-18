import { CATALOG_TABLE_PREFETCH_TRIGGER } from "../../../utils/catalogBooks";

function AccessUsersSkeletonRows({ count = 5, incremental = false }) {
  return Array.from({ length: count }, (_, index) => (
    <tr
      key={`${incremental ? "more" : "initial"}-user-skeleton-${index}`}
      className="processing-skeleton-row processing-table-skeleton-row access-users-table-skeleton-row"
      aria-hidden="true"
    >
      <td data-label="Name">
        <span className="skeleton-line skeleton-line-lg" />
      </td>
      <td data-label="Email">
        <span className="skeleton-line skeleton-line-lg" />
      </td>
      <td data-label="Status">
        <span className="skeleton-line skeleton-line-sm" />
      </td>
      <td data-label="Two-Factor">
        <span className="skeleton-line skeleton-line-sm" />
      </td>
      <td data-label="Account Permissions">
        <div className="access-permission-list">
          <span className="access-permission-chip skeleton-pill" />
          <span className="access-permission-chip skeleton-pill" />
        </div>
      </td>
      <td data-label="Actions">
        <div className="table-actions">
          <span className="ghost-button skeleton-button skeleton-button-sm" />
          <span className="ghost-button skeleton-button skeleton-button-sm" />
        </div>
      </td>
    </tr>
  ));
}

export default function AccessUsersTableCard({
  currentUserId,
  getAccountAccessLabels,
  hasMoreManagedUsers,
  loadingMoreUsers,
  loadingUsers,
  observeUsersLoadTrigger,
  onClearSearch,
  onDeleteUser,
  onEditUser,
  onResendSetupEmail,
  onUpdateUsersSearch,
  onUpdateUsersSort,
  onUpdateUsersStatus,
  refreshingUsers,
  resendingSetupUserId,
  tableShellRef,
  totalManagedUsers,
  userListFilters,
  usersError,
  visibleManagedUsers,
}) {
  const showInitialSkeleton = loadingUsers && !visibleManagedUsers.length;
  const showRefreshSkeletonRows =
    (loadingMoreUsers || refreshingUsers) && visibleManagedUsers.length > 0;

  return (
    <section className="detail-card access-users-card" data-testid="access-users-section">
      <div className="access-users-header">
        <div className="access-users-toolbar">
          <h2 className="access-users-toolbar-title">Users</h2>
          <label
            className="access-users-search-field access-users-toolbar-search"
            aria-label="Search users"
          >
            <span className="catalog-search-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path
                  d="M10.75 4.5a6.25 6.25 0 1 0 0 12.5 6.25 6.25 0 0 0 0-12.5Zm0 1.5a4.75 4.75 0 1 1 0 9.5 4.75 4.75 0 0 1 0-9.5Zm6.86 10.55 2.95 2.95a.75.75 0 1 1-1.06 1.06l-2.95-2.95a.75.75 0 1 1 1.06-1.06Z"
                  fill="currentColor"
                />
              </svg>
            </span>
            <input
              type="search"
              value={userListFilters.q}
              onChange={(event) => onUpdateUsersSearch(event.target.value)}
              onInput={(event) => {
                if (!String(event.target?.value || "").trim()) {
                  onClearSearch();
                }
              }}
              placeholder="Search users by name, email, status, or permission..."
              autoComplete="off"
            />
          </label>
          <div className="catalog-toolbar-field access-users-filter-field">
            <select
              className="catalog-toolbar-select"
              aria-label="Filter users"
              value={userListFilters.status}
              onChange={(event) => onUpdateUsersStatus(event.target.value)}
            >
              <option value="" disabled>
                Filter
              </option>
              <option value="all">All users</option>
              <option value="active">Active</option>
              <option value="disabled">Disabled</option>
              <option value="totp_required">Two-factor required</option>
            </select>
          </div>
          <div className="catalog-toolbar-field access-users-sort-field">
            <select
              className="catalog-toolbar-select"
              aria-label="Sort users"
              value={userListFilters.sort}
              onChange={(event) => onUpdateUsersSort(event.target.value)}
            >
              <option value="" disabled>
                Sort
              </option>
              <option value="name_asc">Name A-Z</option>
              <option value="name_desc">Name Z-A</option>
              <option value="email_asc">Email A-Z</option>
              <option value="email_desc">Email Z-A</option>
              <option value="status">Status</option>
            </select>
          </div>
          <span
            className="access-users-result-count access-users-toolbar-count"
            aria-label={`${totalManagedUsers} users`}
          >
            {showInitialSkeleton ? (
              <span className="skeleton-line skeleton-line-sm" />
            ) : (
              totalManagedUsers
            )}
          </span>
        </div>
      </div>
      <div
        ref={tableShellRef}
        className="processing-table-shell processing-table-shell--mobile-cards access-users-table-shell"
        aria-busy={loadingUsers || loadingMoreUsers || refreshingUsers}
      >
        <table
          className="simple-table access-users-table table-mobile-cards"
          data-testid="access-users-table"
        >
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Status</th>
              <th>Two-Factor</th>
              <th>Account Permissions</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {showInitialSkeleton ? (
              <AccessUsersSkeletonRows />
            ) : visibleManagedUsers.length ? (
              visibleManagedUsers.map((entry, rowIndex) => {
                const accountAccessLabels = getAccountAccessLabels(entry);

                return (
                  <tr
                    key={entry.id}
                    ref={
                      hasMoreManagedUsers &&
                      rowIndex ===
                        Math.max(
                          0,
                          visibleManagedUsers.length -
                            CATALOG_TABLE_PREFETCH_TRIGGER,
                        )
                        ? observeUsersLoadTrigger
                        : undefined
                    }
                  >
                    <td data-label="Name">{entry.full_name || "-"}</td>
                    <td data-label="Email">{entry.email}</td>
                    <td data-label="Status">
                      {entry.is_active ? "Active" : "Disabled"}
                    </td>
                    <td data-label="Two-Factor">
                      {entry.totp_required
                        ? "Required"
                        : entry.totp_enabled
                          ? "Enabled"
                          : "Optional"}
                    </td>
                    <td
                      className="access-permission-cell"
                      data-label="Account Permissions"
                    >
                      {accountAccessLabels.length ? (
                        <div
                          className="access-permission-list"
                          data-testid={`access-user-permissions-${entry.id}`}
                          aria-label={`Account permissions: ${accountAccessLabels.join(", ")}`}
                        >
                          {accountAccessLabels.map((label) => (
                            <span
                              key={`${entry.id}-${label}`}
                              className="access-permission-chip"
                            >
                              {label}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="access-permission-empty">-</span>
                      )}
                    </td>
                    <td data-label="Actions">
                      <div className="table-actions">
                        {`${entry.id}` === `${currentUserId}` ||
                        entry.is_superuser ? (
                          <span className="table-note">Locked</span>
                        ) : (
                          <>
                            {entry.can_resend_setup_email ? (
                              <button
                                type="button"
                                className="ghost-button"
                                onClick={() => onResendSetupEmail(entry)}
                                disabled={`${resendingSetupUserId}` === `${entry.id}`}
                              >
                                {`${resendingSetupUserId}` === `${entry.id}`
                                  ? "Sending..."
                                  : "Resend Email"}
                              </button>
                            ) : null}
                            <button
                              type="button"
                              className="primary-button"
                              onClick={() => onEditUser(entry)}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="ghost-button danger-button"
                              onClick={() => onDeleteUser(entry)}
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={6} className="table-empty-cell">
                  {usersError || "No users found for the current search and filter."}
                </td>
              </tr>
            )}
            {showRefreshSkeletonRows ? (
              <AccessUsersSkeletonRows count={3} incremental />
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
