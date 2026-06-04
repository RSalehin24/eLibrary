export default function AccessHero({ activeTab, onSelectTab }) {
  return (
    <section className="detail-card admin-hero-card">
      <div className="admin-hero-copy">
        <h1>Users &amp; Access</h1>
      </div>
      <div
        className="admin-tab-grid"
        role="tablist"
        aria-label="Users and access sections"
      >
        <button
          type="button"
          data-testid="access-users-tab"
          className={
            activeTab === "users"
              ? "admin-tab-card is-active"
              : "admin-tab-card"
          }
          onClick={() => onSelectTab("users")}
          aria-pressed={activeTab === "users"}
        >
          <span className="admin-tab-label">Users</span>
        </button>
        <button
          type="button"
          data-testid="access-rules-tab"
          className={
            activeTab === "access"
              ? "admin-tab-card is-active"
              : "admin-tab-card"
          }
          onClick={() => onSelectTab("access")}
          aria-pressed={activeTab === "access"}
        >
          <span className="admin-tab-label">Access Rules</span>
        </button>
      </div>
    </section>
  );
}
