import AppShell from "./layouts/AppShell";
import AppRoutes from "./features/app/AppRoutes";
import BackendStatusModal from "./features/app/BackendStatusModal";
import ErrorBoundary from "./components/ErrorBoundary";
import ThemeToggle from "./components/ThemeToggle";
import ScrollToTopButton from "./components/ScrollToTopButton";
import RouteScrollReset from "./features/app/RouteScrollReset";
import SessionRestartHandler from "./features/app/SessionRestartHandler";

export default function App() {
  return (
    <AppShell>
      <RouteScrollReset />
      <SessionRestartHandler />
      <BackendStatusModal />
      <ErrorBoundary>
        <AppRoutes />
      </ErrorBoundary>
      <div className="floating-actions">
        <ThemeToggle className="theme-toggle-floating" />
        <ScrollToTopButton />
      </div>
    </AppShell>
  );
}
