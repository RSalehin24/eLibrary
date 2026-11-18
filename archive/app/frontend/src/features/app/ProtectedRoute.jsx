import { Navigate, useLocation } from "react-router-dom";
import PageLoader from "../../components/PageLoader";
import { useSession } from "../../hooks/useSession";

export default function ProtectedRoute({ children }) {
  const { authenticated, loading, user } = useSession();
  const location = useLocation();

  if (loading) {
    return (
      <PageLoader
        label="Loading your session"
        detail="Checking sign-in and workspace access."
        variant="auth"
      />
    );
  }

  if (!authenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (
    user?.totp_setup_required &&
    location.pathname !== "/two-factor-setup"
  ) {
    return (
      <Navigate
        to="/two-factor-setup"
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return children;
}
