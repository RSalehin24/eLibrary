import { NavLink } from "react-router-dom";
import { initialsForUser } from "./utils";

function ProfileAvatar({ displayName, profileImageUrl, large = false }) {
  const className = large
    ? "profile-avatar profile-avatar-large"
    : "profile-avatar";

  if (profileImageUrl) {
    return <img className={className} src={profileImageUrl} alt={displayName} />;
  }

  return <div className={className}>{initialsForUser(displayName)}</div>;
}

function SignOutIcon() {
  return (
    <span className="profile-menu-icon" aria-hidden="true">
      <svg
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M8 4.75H5.75A1.75 1.75 0 0 0 4 6.5v7a1.75 1.75 0 0 0 1.75 1.75H8" />
        <path d="M11 6.5 15 10l-4 3.5" />
        <path d="M14.75 10H8.5" />
      </svg>
    </span>
  );
}

export default function ProfileMenu({
  displayName,
  email,
  profileImageUrl,
  alertsMuted = false,
  menuOpen,
  menuRef,
  onToggle,
  onClose,
  onToggleAlerts,
  onLogout,
}) {
  return (
    <div ref={menuRef} className="profile-menu-shell">
      <button
        type="button"
        className="profile-menu-trigger"
        onClick={onToggle}
        aria-expanded={menuOpen}
        aria-haspopup="menu"
        aria-label={menuOpen ? "Close profile menu" : "Open profile menu"}
        data-testid="profile-menu-trigger"
      >
        <ProfileAvatar
          displayName={displayName}
          profileImageUrl={profileImageUrl}
        />
      </button>
      {menuOpen ? (
        <div className="profile-menu-dropdown" role="menu">
          <div className="profile-menu-summary">
            <ProfileAvatar
              displayName={displayName}
              profileImageUrl={profileImageUrl}
              large
            />
            <div className="profile-menu-meta">
              <strong>{displayName}</strong>
              <span>{email}</span>
            </div>
          </div>
          <div className="profile-menu-actions">
            <NavLink to="/profile" className="profile-menu-link" onClick={onClose}>
              Profile
            </NavLink>
            <label className="profile-menu-toggle-row">
              <div className="profile-menu-toggle-copy">
                <span className="profile-menu-toggle-title">Alerts</span>
              </div>
              <span className="profile-menu-toggle">
                <input
                  type="checkbox"
                  role="switch"
                  checked={!alertsMuted}
                  onChange={onToggleAlerts}
                  data-testid="profile-alerts-toggle"
                />
                <span className="profile-menu-toggle-track" aria-hidden="true">
                  <span className="profile-menu-toggle-state">
                    {alertsMuted ? "Off" : "On"}
                  </span>
                  <span className="profile-menu-toggle-thumb" />
                </span>
              </span>
            </label>
            <div className="profile-menu-divider" />
            <button
              type="button"
              className="profile-menu-link profile-menu-signout"
              onClick={onLogout}
            >
              <SignOutIcon />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
