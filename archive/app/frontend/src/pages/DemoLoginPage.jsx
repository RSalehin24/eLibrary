import { useEffect, useRef } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import LoadingSpinner from "../components/LoadingSpinner";
import { authApi } from "../api/client";
import { useSession } from "../hooks/useSession";
import { useToast } from "../hooks/useToast";

export default function DemoLoginPage() {
  const navigate = useNavigate();
  const attempted = useRef(false);
  const { loading, authenticated, user, refreshSession } = useSession();
  const toast = useToast();

  useEffect(() => {
    if (!loading && !authenticated && !attempted.current) {
      attempted.current = true;
      authApi
        .demoLogin()
        .then(() => refreshSession())
        .catch(() => {
          toast.error("Demo login failed. Please sign in manually.");
          navigate("/login", { replace: true });
        });
    }
  }, [loading, authenticated, navigate, refreshSession, toast]);

  if (loading) {
    return (
      <div className="login-shell">
        <div className="detail-card login-card">
          <LoadingSpinner size={24} />
        </div>
      </div>
    );
  }

  if (authenticated) {
    const homePath = user?.is_superuser ? "/home" : "/my-books";
    return <Navigate to={homePath} replace />;
  }

  return (
    <div className="login-shell">
      <div className="detail-card login-card">
        <LoadingSpinner size={24} />
      </div>
    </div>
  );
}
