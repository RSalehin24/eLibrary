import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useSession } from "../../hooks/useSession";
import { useToast } from "../../hooks/useToast";

export default function SessionRestartHandler() {
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();
  const { expireSession } = useSession();

  useEffect(() => {
    function handleSessionExpired() {
      const message = "The application has restarted. Please log in again.";
      expireSession(message);
      toast.info(message);
      if (location.pathname !== "/login") {
        navigate("/login", {
          replace: true,
          state: { from: location.pathname, reason: "app-restarted" },
        });
      }
    }

    window.addEventListener("app:session-expired", handleSessionExpired);
    return () =>
      window.removeEventListener("app:session-expired", handleSessionExpired);
  }, [expireSession, location.pathname, navigate, toast]);

  return null;
}
