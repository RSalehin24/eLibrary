import { useEffect, useRef, useState } from "react";
import { probeBackendHealth } from "../../api/client";

export default function BackendStatusModal() {
  const [status, setStatus] = useState(null);
  const shouldRefreshOnRecoveryRef = useRef(false);

  useEffect(() => {
    function handleBackendStatus(event) {
      const detail = event.detail || {};
      if (detail.state === "up") {
        if (shouldRefreshOnRecoveryRef.current) {
          shouldRefreshOnRecoveryRef.current = false;
          window.location.reload();
          return;
        }
        setStatus(null);
        return;
      }
      if (detail.state === "down") {
        shouldRefreshOnRecoveryRef.current = true;
        setStatus({ mode: detail.mode || "outage" });
      }
    }

    window.addEventListener("app:backend-status", handleBackendStatus);
    return () => {
      window.removeEventListener("app:backend-status", handleBackendStatus);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const checkHealth = async () => {
      const healthy = await probeBackendHealth();
      if (cancelled) {
        return;
      }
      if (!healthy) {
        shouldRefreshOnRecoveryRef.current = true;
        setStatus((current) => current || { mode: "outage" });
      } else {
        setStatus(null);
      }
    };

    checkHealth();
    const healthInterval = window.setInterval(checkHealth, 6000);
    return () => {
      cancelled = true;
      window.clearInterval(healthInterval);
    };
  }, []);

  useEffect(() => {
    if (!status) {
      return undefined;
    }

    let cancelled = false;
    const timer = window.setInterval(async () => {
      const healthy = await probeBackendHealth();
      if (healthy && !cancelled) {
        if (shouldRefreshOnRecoveryRef.current) {
          shouldRefreshOnRecoveryRef.current = false;
          window.location.reload();
          return;
        }
        setStatus(null);
      }
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [status]);

  if (!status) {
    return null;
  }

  const waitingMessage =
    status.mode === "restarting"
      ? "Please wait a few minutes while the server restarts."
      : "Please wait a few hours and try again.";

  return (
    <div className="backend-status-overlay" role="presentation">
      <section
        className="backend-status-modal"
        role="alertdialog"
        aria-modal="true"
        aria-live="assertive"
      >
        <h2>There is an error.</h2>
        <p>{waitingMessage}</p>
      </section>
    </div>
  );
}
