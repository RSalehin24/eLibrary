import { useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { authApi } from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";
import PageLoader from "../components/PageLoader";
import TwoFactorSetupPanel from "../components/TwoFactorSetupPanel";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSession } from "../hooks/useSession";
import { useToast } from "../hooks/useToast";
import { humanizeError } from "../utils/humanizeError";

const emptySetup = {
  provisioning_uri: "",
  secret: "",
  qr_svg: "",
};

export default function TwoFactorSetupPage() {
  usePageTitle("Two-factor setup");
  const location = useLocation();
  const navigate = useNavigate();
  const { authenticated, loading, refreshSession, user } = useSession();
  const toast = useToast();
  const autoPreparedRef = useRef(false);
  const [setup, setSetup] = useState(emptySetup);
  const [token, setToken] = useState("");
  const [totpAction, setTotpAction] = useState("");
  const [bootstrapping, setBootstrapping] = useState(true);
  const [setupError, setSetupError] = useState("");

  async function prepareSetup() {
    if (totpAction) {
      return;
    }

    try {
      setTotpAction("setup");
      setSetupError("");
      const payload = await authApi.twoFactorSetup();
      setSetup(payload);
    } catch (error) {
      setSetupError(error.message);
      toast.error(humanizeError(error));
    } finally {
      setTotpAction("");
      setBootstrapping(false);
    }
  }

  useEffect(() => {
    if (!authenticated || !user?.totp_setup_required) {
      autoPreparedRef.current = false;
      setBootstrapping(false);
      return;
    }

    if (autoPreparedRef.current) {
      return;
    }

    autoPreparedRef.current = true;
    prepareSetup().catch(() => {});
  }, [authenticated, user?.id, user?.totp_setup_required]);

  async function confirmSetup(event) {
    event.preventDefault();
    if (totpAction) {
      return;
    }

    try {
      setTotpAction("verify");
      await authApi.twoFactorConfirm({ token });
      await refreshSession();
      toast.success("Two-factor enabled.");
      navigate(location.state?.from || "/home", { replace: true });
    } catch (error) {
      toast.error(humanizeError(error));
    } finally {
      setTotpAction("");
    }
  }

  async function copyProvisioningUrl() {
    try {
      await navigator.clipboard.writeText(setup.provisioning_uri);
      toast.success("Setup URL copied.");
    } catch {
      toast.error("Could not copy the setup URL.");
    }
  }

  if (loading) {
    return (
      <PageLoader
        label="Loading session"
        detail="Checking your security requirements."
        variant="auth"
      />
    );
  }

  if (!authenticated) {
    return (
      <Navigate to="/login" replace state={{ from: "/two-factor-setup" }} />
    );
  }

  if (!user?.totp_setup_required) {
    return <Navigate to="/home" replace />;
  }

  return (
    <div className="login-shell">
      <section className="detail-card login-card auth-setup-card">
        <p className="eyebrow">Security setup</p>
        <h1>Set up two-factor authentication</h1>

        {bootstrapping && !setup.provisioning_uri ? (
          <PageLoader
            label="Preparing your setup"
            detail="Generating your QR code and secret."
            variant="card"
            className="auth-setup-loader"
          />
        ) : null}

        {!bootstrapping && !setup.provisioning_uri ? (
          <div className="page-stack">
            {setupError ? <p className="form-feedback">{setupError}</p> : null}
            <div className="inline-pills">
              <button
                type="button"
                className="primary-button"
                onClick={prepareSetup}
                disabled={Boolean(totpAction)}
              >
                <span className="button-label">
                  {totpAction === "setup" ? <LoadingSpinner size={14} /> : null}
                  {totpAction === "setup" ? "Preparing..." : "Prepare setup"}
                </span>
              </button>
            </div>
          </div>
        ) : null}

        {setup.provisioning_uri ? (
          <TwoFactorSetupPanel
            confirmLabel="Verify and Continue"
            description="Scan the QR code, then enter the current six-digit code from your authenticator app."
            onCopy={copyProvisioningUrl}
            onSubmit={confirmSetup}
            onTokenChange={setToken}
            required
            setup={setup}
            stacked
            token={token}
            totpAction={totpAction}
            title="Authenticator app"
          />
        ) : null}
      </section>
    </div>
  );
}
