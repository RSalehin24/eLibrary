import { NavLink } from "react-router-dom";
import NavDropdown from "./NavDropdown";
import ProfileMenu from "./ProfileMenu";
import { MenuIcon } from "./MobileNavigationIcons";
import { bookPropertiesItems, getHomePath } from "./navigation";

export function AppTopbar({
  authenticated,
  displayName,
  hasProcessingNav,
  isBookPropertiesActive,
  isLoginRoute,
  isProcessingPropertiesActive,
  isReaderRoute,
  isSuperUser,
  menuOpen,
  mobileNavOpen,
  navigation,
  onLogout,
  onProfileMenuClose,
  onProfileMenuToggle,
  onPropertiesItemClick,
  onPropertiesToggle,
  onProcessingItemClick,
  onProcessingToggle,
  onToggleMobileNav,
  primaryNav,
  processingOpen,
  processingMenuRef,
  profileMenuRef,
  propertiesMenuRef,
  propertiesOpen,
  secondaryNav,
  showMobileNav,
  toast,
  useAppTopbar,
  useMinimalTopbar,
  user,
  visibleProcessingItems,
}) {
  return (
    <header
      className={useAppTopbar ? "topbar topbar-app" : "topbar topbar-public"}
    >
      <div
        className={
          isReaderRoute ? "brand-block brand-block-reader" : "brand-block"
        }
      >
        <NavLink to={getHomePath(user)} className="brand-mark">
          <span className="brand-mark-name">RSalehin24</span>
          <span className="brand-mark-suffix">Library</span>
        </NavLink>
      </div>
      {showMobileNav ? (
        <button
          type="button"
          className={`mobile-nav-trigger${mobileNavOpen ? " is-active" : ""}`}
          onClick={onToggleMobileNav}
          aria-expanded={mobileNavOpen}
          aria-controls="app-mobile-nav"
          aria-label={mobileNavOpen ? "Close menu" : "Open menu"}
          data-testid="mobile-nav-trigger"
        >
          <MenuIcon open={mobileNavOpen} />
        </button>
      ) : null}
      {useAppTopbar ? (
        <nav className="topnav" aria-label="Primary">
          {primaryNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "nav-link is-active" : "nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
          <NavDropdown
            menuRef={propertiesMenuRef}
            active={isBookPropertiesActive}
            open={propertiesOpen}
            label="Book Properties"
            items={bookPropertiesItems}
            onToggle={onPropertiesToggle}
            onItemClick={onPropertiesItemClick}
          />
          {hasProcessingNav ? (
            <NavDropdown
              menuRef={processingMenuRef}
              active={isProcessingPropertiesActive}
              open={processingOpen}
              label="Processing"
              items={visibleProcessingItems}
              onToggle={onProcessingToggle}
              onItemClick={onProcessingItemClick}
            />
          ) : null}
          {secondaryNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "nav-link is-active" : "nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      ) : null}
      {!useMinimalTopbar ? (
        <div className="session-box">
          {authenticated ? (
            <>
              {isSuperUser ? (
                <>
                  <NavLink
                    to="/my-books"
                    className={({ isActive }) =>
                      isActive ? "nav-link is-active" : "nav-link"
                    }
                  >
                    My Books
                  </NavLink>
                  <NavLink
                    to="/kindle-sent"
                    className={({ isActive }) =>
                      isActive ? "nav-link is-active" : "nav-link"
                    }
                  >
                    Kindle
                  </NavLink>
                  <NavLink
                    to="/notes"
                    className={({ isActive }) =>
                      isActive ? "nav-link is-active" : "nav-link"
                    }
                  >
                    My Notes
                  </NavLink>
                </>
              ) : null}
              <ProfileMenu
                displayName={displayName}
                email={user?.email}
                profileImageUrl={user?.profile_image_url}
                alertsMuted={toast.muted}
                menuOpen={menuOpen}
                menuRef={profileMenuRef}
                onToggle={onProfileMenuToggle}
                onClose={onProfileMenuClose}
                onToggleAlerts={toast.toggleMuted}
                onLogout={onLogout}
              />
            </>
          ) : !isLoginRoute ? (
            <NavLink to="/login" className="ghost-button">
              Sign in
            </NavLink>
          ) : null}
        </div>
      ) : null}
    </header>
  );
}
