import { NavLink } from "react-router-dom";
import {
  ChevronIcon,
  MenuIcon,
  MobileProfileSummary,
} from "./MobileNavigationIcons";
import { bookPropertiesItems } from "./navigation";

function MobileNavGroup({
  active,
  items,
  label,
  onClose,
  onToggle,
  open,
  prefix,
}) {
  return (
    <div className="mobile-nav-section">
      <button
        type="button"
        className={`mobile-nav-group-toggle${active ? " is-active" : ""}${
          open ? " is-open" : ""
        }`}
        onClick={onToggle}
        aria-expanded={open}
      >
        <span>{label}</span>
        <span className="mobile-nav-group-caret" aria-hidden="true">
          <ChevronIcon open={open} />
        </span>
      </button>
      <div className={`mobile-nav-group-panel${open ? " is-open" : ""}`}>
        {items.map((item) => (
          <NavLink
            key={`${prefix}-${item.to}`}
            to={item.to}
            className={({ isActive }) =>
              isActive ? "mobile-nav-sub-link is-active" : "mobile-nav-sub-link"
            }
            onClick={onClose}
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </div>
  );
}

export function MobileNavigationPanel({
  displayName,
  email,
  hasProcessingNav,
  isBookPropertiesActive,
  isProcessingPropertiesActive,
  isSuperUser,
  mobileNavOpen,
  mobileProcessingOpen,
  mobilePropertiesOpen,
  navigation,
  onClose,
  onLogout,
  onProcessingToggle,
  onPropertiesToggle,
  profileImageUrl,
  toast,
  visibleProcessingItems,
}) {
  return (
    <>
      <button
        type="button"
        className={`mobile-nav-backdrop${mobileNavOpen ? " is-open" : ""}`}
        aria-hidden={mobileNavOpen ? "false" : "true"}
        tabIndex={mobileNavOpen ? 0 : -1}
        onClick={onClose}
      />
      <div
        id="app-mobile-nav"
        className={`mobile-nav-panel${mobileNavOpen ? " is-open" : ""}`}
        aria-hidden={mobileNavOpen ? "false" : "true"}
      >
        <div className="mobile-nav-panel-header">
          <MobileProfileSummary
            displayName={displayName}
            email={email}
            profileImageUrl={profileImageUrl}
          />
          <button
            type="button"
            className="mobile-nav-close"
            onClick={onClose}
            aria-label="Close menu"
          >
            <MenuIcon open />
          </button>
        </div>

        <div className="mobile-nav-links">
          {navigation.map((item) => (
            <NavLink
              key={`mobile-${item.to}`}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "mobile-nav-link is-active" : "mobile-nav-link"
              }
              onClick={onClose}
            >
              {item.label}
            </NavLink>
          ))}
          {isSuperUser ? (
            <>
              <NavLink
                to="/my-books"
                className={({ isActive }) =>
                  isActive ? "mobile-nav-link is-active" : "mobile-nav-link"
                }
                onClick={onClose}
              >
                My Books
              </NavLink>
              <NavLink
                to="/kindle-sent"
                className={({ isActive }) =>
                  isActive ? "mobile-nav-link is-active" : "mobile-nav-link"
                }
                onClick={onClose}
              >
                Kindle
              </NavLink>
              <NavLink
                to="/notes"
                className={({ isActive }) =>
                  isActive ? "mobile-nav-link is-active" : "mobile-nav-link"
                }
                onClick={onClose}
              >
                My Notes
              </NavLink>
            </>
          ) : null}
        </div>

        <MobileNavGroup
          active={isBookPropertiesActive}
          items={bookPropertiesItems}
          label="Book Properties"
          onClose={onClose}
          onToggle={onPropertiesToggle}
          open={mobilePropertiesOpen}
          prefix="book-properties"
        />

        {hasProcessingNav ? (
          <MobileNavGroup
            active={isProcessingPropertiesActive}
            items={visibleProcessingItems}
            label="Processing"
            onClose={onClose}
            onToggle={onProcessingToggle}
            open={mobileProcessingOpen}
            prefix="processing"
          />
        ) : null}

        <div className="mobile-nav-session">
          <NavLink
            to="/profile"
            className={({ isActive }) =>
              isActive ? "mobile-nav-link is-active" : "mobile-nav-link"
            }
            onClick={onClose}
          >
            Profile
          </NavLink>
          <label className="profile-menu-toggle-row mobile-nav-alerts-row">
            <div className="profile-menu-toggle-copy">
              <span className="profile-menu-toggle-title">Alerts</span>
            </div>
            <span className="profile-menu-toggle">
              <input
                type="checkbox"
                role="switch"
                checked={!toast.muted}
                onChange={toast.toggleMuted}
                data-testid="mobile-profile-alerts-toggle"
              />
              <span className="profile-menu-toggle-track" aria-hidden="true">
                <span className="profile-menu-toggle-state">
                  {toast.muted ? "Off" : "On"}
                </span>
                <span className="profile-menu-toggle-thumb" />
              </span>
            </span>
          </label>
          <button
            type="button"
            className="mobile-nav-link mobile-nav-logout"
            onClick={onLogout}
          >
            Sign Out
          </button>
        </div>
      </div>
    </>
  );
}
