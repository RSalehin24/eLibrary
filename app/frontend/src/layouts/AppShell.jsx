import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AppTopbar } from "../features/layout/AppTopbar";
import { MobileNavigationPanel } from "../features/layout/MobileNavigationPanel";
import { ReaderTopbarHideButton } from "../features/layout/ReaderTopbarHideButton";
import {
  authenticatedNavigation,
  isBookPropertiesRoute,
  isProcessingRoute,
  processingItems,
} from "../features/layout/navigation";
import { useSession } from "../hooks/useSession";
import { useToast } from "../hooks/useToast";
import { hasCapability } from "../utils/capabilities";

export default function AppShell({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { authenticated, user, logout } = useSession();
  const toast = useToast();
  const isReaderRoute = location.pathname === "/reader";
  const isCreatePasswordRoute = location.pathname === "/create-password";
  const isTotpSetupRoute = location.pathname === "/two-factor-setup";
  const readerNavHidden =
    isReaderRoute &&
    new URLSearchParams(location.search).get("appNav") !== "shown";
  const showTopbar = !readerNavHidden;
  const useMinimalTopbar = isTotpSetupRoute || isCreatePasswordRoute;
  const [menuOpen, setMenuOpen] = useState(false);
  const [propertiesOpen, setPropertiesOpen] = useState(false);
  const [processingOpen, setProcessingOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [mobilePropertiesOpen, setMobilePropertiesOpen] = useState(false);
  const [mobileProcessingOpen, setMobileProcessingOpen] = useState(false);
  const profileMenuRef = useRef(null);
  const propertiesMenuRef = useRef(null);
  const processingMenuRef = useRef(null);
  const canManageProcessing = hasCapability(user, "processing:manage");
  const visibleProcessingItems = processingItems.filter(
    (item) => !item.capabilityRequired || canManageProcessing,
  );
  const hasProcessingNav = visibleProcessingItems.length > 0;
  const navigation = authenticated ? authenticatedNavigation(user) : [];
  const isBookPropertiesActive = isBookPropertiesRoute(location.pathname);
  const isProcessingPropertiesActive = isProcessingRoute(location.pathname);
  const isLoginRoute = location.pathname === "/login";
  const useAppTopbar = authenticated && !useMinimalTopbar;
  const showMobileNav = useAppTopbar && showTopbar;
  const isSuperUser = Boolean(user?.is_superuser);
  const displayName = user?.full_name || user?.email || "";

  useEffect(() => {
    setMenuOpen(false);
    setPropertiesOpen(false);
    setProcessingOpen(false);
    setMobileNavOpen(false);
    setMobilePropertiesOpen(false);
    setMobileProcessingOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen && !propertiesOpen && !processingOpen) {
      return undefined;
    }

    function handlePointerDown(event) {
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(event.target)
      ) {
        setMenuOpen(false);
      }
      if (
        propertiesMenuRef.current &&
        !propertiesMenuRef.current.contains(event.target)
      ) {
        setPropertiesOpen(false);
      }
      if (
        processingMenuRef.current &&
        !processingMenuRef.current.contains(event.target)
      ) {
        setProcessingOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, [menuOpen, propertiesOpen, processingOpen]);

  useEffect(() => {
    if (!mobileNavOpen) {
      return undefined;
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setMobileNavOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [mobileNavOpen]);

  useEffect(() => {
    if (!mobileNavOpen) {
      return undefined;
    }

    const mediaQuery = window.matchMedia("(min-width: 981px)");
    function handleChange(event) {
      if (event.matches) {
        setMobileNavOpen(false);
      }
    }

    mediaQuery.addEventListener("change", handleChange);
    return () => {
      mediaQuery.removeEventListener("change", handleChange);
    };
  }, [mobileNavOpen]);

  useEffect(() => {
    document.body.classList.toggle("app-mobile-nav-open", mobileNavOpen);
    return () => {
      document.body.classList.remove("app-mobile-nav-open");
    };
  }, [mobileNavOpen]);

  useEffect(() => {
    if (!showMobileNav && mobileNavOpen) {
      setMobileNavOpen(false);
    }
  }, [showMobileNav, mobileNavOpen]);

  useEffect(() => {
    if (!mobileNavOpen) {
      return;
    }

    if (isBookPropertiesActive) {
      setMobilePropertiesOpen(true);
    }
    if (isProcessingPropertiesActive) {
      setMobileProcessingOpen(true);
    }
  }, [mobileNavOpen, isBookPropertiesActive, isProcessingPropertiesActive]);

  function hideReaderTopbar() {
    if (!isReaderRoute) {
      return;
    }

    const nextParams = new URLSearchParams(location.search);
    nextParams.set("appNav", "hidden");
    navigate(
      {
        pathname: location.pathname,
        search: `?${nextParams.toString()}`,
      },
      { replace: true },
    );
  }

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
  }

  async function handleMobileLogout() {
    setMobileNavOpen(false);
    await logout();
  }

  return (
    <div className={isReaderRoute ? "shell shell-reader-mode" : "shell"}>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      {!isReaderRoute ? (
        <div
          className="shell-ornament shell-ornament-left"
          aria-hidden="true"
        />
      ) : null}
      {!isReaderRoute ? (
        <div
          className="shell-ornament shell-ornament-right"
          aria-hidden="true"
        />
      ) : null}
      {showTopbar ? (
        <AppTopbar
          authenticated={authenticated}
          displayName={displayName}
          hasProcessingNav={hasProcessingNav}
          isBookPropertiesActive={isBookPropertiesActive}
          isLoginRoute={isLoginRoute}
          isProcessingPropertiesActive={isProcessingPropertiesActive}
          isReaderRoute={isReaderRoute}
          isSuperUser={isSuperUser}
          menuOpen={menuOpen}
          mobileNavOpen={mobileNavOpen}
          navigation={navigation}
          onLogout={handleLogout}
          onProfileMenuClose={() => setMenuOpen(false)}
          onProfileMenuToggle={() => setMenuOpen((current) => !current)}
          onPropertiesItemClick={() => setPropertiesOpen(false)}
          onPropertiesToggle={() => setPropertiesOpen((current) => !current)}
          onProcessingItemClick={() => setProcessingOpen(false)}
          onProcessingToggle={() => setProcessingOpen((current) => !current)}
          onToggleMobileNav={() => setMobileNavOpen((current) => !current)}
          processingMenuRef={processingMenuRef}
          processingOpen={processingOpen}
          profileMenuRef={profileMenuRef}
          propertiesMenuRef={propertiesMenuRef}
          propertiesOpen={propertiesOpen}
          showMobileNav={showMobileNav}
          toast={toast}
          useAppTopbar={useAppTopbar}
          useMinimalTopbar={useMinimalTopbar}
          user={user}
          visibleProcessingItems={visibleProcessingItems}
        />
      ) : null}
      {showMobileNav ? (
        <MobileNavigationPanel
          displayName={displayName}
          email={user?.email}
          hasProcessingNav={hasProcessingNav}
          isBookPropertiesActive={isBookPropertiesActive}
          isProcessingPropertiesActive={isProcessingPropertiesActive}
          isSuperUser={isSuperUser}
          mobileNavOpen={mobileNavOpen}
          mobileProcessingOpen={mobileProcessingOpen}
          mobilePropertiesOpen={mobilePropertiesOpen}
          navigation={navigation}
          onClose={() => setMobileNavOpen(false)}
          onLogout={handleMobileLogout}
          onProcessingToggle={() =>
            setMobileProcessingOpen((current) => !current)
          }
          onPropertiesToggle={() =>
            setMobilePropertiesOpen((current) => !current)
          }
          profileImageUrl={user?.profile_image_url}
          toast={toast}
          visibleProcessingItems={visibleProcessingItems}
        />
      ) : null}
      {isReaderRoute && showTopbar ? (
        <ReaderTopbarHideButton onClick={hideReaderTopbar} />
      ) : null}
      <main
        id="main-content"
        tabIndex={-1}
        className={
          isReaderRoute ? "page-shell page-shell-reader" : "page-shell"
        }
      >
        {children}
      </main>
    </div>
  );
}
