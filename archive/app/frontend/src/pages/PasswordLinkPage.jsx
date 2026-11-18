import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { authApi } from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";
import PageLoader from "../components/PageLoader";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSession } from "../hooks/useSession";
import { useToast } from "../hooks/useToast";
import { humanizeError } from "../utils/humanizeError";
import { PASSWORD_LINK_COPY } from "./passwordLinkCopy";

export default function PasswordLinkPage({ mode = "reset" }) {
  usePageTitle(mode === "reset" ? "Set new password" : "Create password");
  const navigate = useNavigate();
  const { authenticated, loading, logout, refreshSession } = useSession();
  const [params] = useSearchParams();
  const toast = useToast();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [validatingLink, setValidatingLink] = useState(false);
  const [linkState, setLinkState] = useState(() =>
    params.get("uid") && params.get("token") ? "idle" : "invalid",
  );

  const resetPayload = useMemo(
    () => ({
      uid: params.get("uid") || "",
      token: params.get("token") || "",
    }),
    [params],
  );

  const copy = PASSWORD_LINK_COPY[mode] || PASSWORD_LINK_COPY.reset;
  const hasResetLink = Boolean(resetPayload.uid && resetPayload.token);

  function isExpiredLinkError(error) {
    return [
      "Invalid reset link.",
      "Reset token is invalid or expired.",
    ].includes(error?.message);
  }

  async function handleLogout() {
    if (loggingOut) {
      return;
    }
    try {
      setLoggingOut(true);
      await logout();
      toast.info("Signed out. You can now continue with this password link.");
    } catch (error) {
      toast.error(humanizeError(error));
    } finally {
      setLoggingOut(false);
    }
  }

  useEffect(() => {
    if (loading || authenticated) {
      return undefined;
    }

    if (!hasResetLink) {
      setLinkState("invalid");
      setValidatingLink(false);
      return undefined;
    }

    let cancelled = false;
    setValidatingLink(true);
    setLinkState("idle");

    void authApi
      .passwordResetValidate(resetPayload)
      .then(() => {
        if (cancelled) {
          return;
        }
        setLinkState("valid");
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        if (!isExpiredLinkError(error)) {
          toast.error(humanizeError(error));
        }
        setLinkState("invalid");
      })
      .finally(() => {
        if (!cancelled) {
          setValidatingLink(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [authenticated, hasResetLink, loading, resetPayload, toast]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) {
      return;
    }

    if (!hasResetLink || linkState !== "valid") {
      setLinkState("invalid");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("The password fields must match.");
      return;
    }

    try {
      setSubmitting(true);
      const payload = await authApi.passwordResetConfirm({
        ...resetPayload,
        new_password: password,
      });

      if (payload?.next_step === "totp_setup") {
        await refreshSession();
        toast.success(copy.totpSetupMessage);
        navigate("/two-factor-setup", { replace: true });
        return;
      }

      toast.success(copy.successMessage);
      navigate("/login", { replace: true });
    } catch (error) {
      if (isExpiredLinkError(error)) {
        setLinkState("invalid");
        return;
      }
      toast.error(humanizeError(error, "Request failed."));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <PageLoader
        label="Loading session"
        detail="Checking account status."
        variant="auth"
      />
    );
  }

  if (authenticated) {
    return (
      <div className="login-shell">
        <section className="detail-card login-card">
          <p className="eyebrow">{copy.eyebrow}</p>
          <h1>Log out first</h1>
          <p className="muted-copy">
            You are currently signed in. Log out before using this password
            link.
          </p>
          <div className="inline-pills">
            <button
              type="button"
              className="primary-button"
              onClick={handleLogout}
              disabled={loggingOut}
            >
              <span className="button-label">
                {loggingOut ? <LoadingSpinner size={16} /> : null}
                {loggingOut ? "Logging out..." : "Log out"}
              </span>
            </button>
            <Link to="/home" className="ghost-button">
              Back
            </Link>
          </div>
        </section>
      </div>
    );
  }

  if (validatingLink) {
    return (
      <PageLoader
        label="Checking link"
        detail="Validating password link."
        variant="auth"
      />
    );
  }

  if (linkState === "invalid") {
    return (
      <div className="login-shell">
        <section className="detail-card login-card password-link-expired-card">
          <h1>{copy.invalidHeading}</h1>
        </section>
      </div>
    );
  }

  return (
    <div className="login-shell">
      <section className="detail-card login-card">
        <p className="eyebrow">{copy.eyebrow}</p>
        <h1>{copy.heading}</h1>
        <form className="stack-form" onSubmit={handleSubmit}>
          <label>
            <span>New password</span>
            <div className="password-input-row">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="new-password"
              />
              <button
                type="button"
                className="password-visibility-button"
                onClick={() => setShowPassword((current) => !current)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          <label>
            <span>Confirm password</span>
            <div className="password-input-row">
              <input
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
              />
              <button
                type="button"
                className="password-visibility-button"
                onClick={() => setShowConfirmPassword((current) => !current)}
                aria-label={
                  showConfirmPassword
                    ? "Hide confirmed password"
                    : "Show confirmed password"
                }
              >
                {showConfirmPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          <div className="inline-pills">
            <button
              type="submit"
              className="primary-button"
              disabled={submitting}
            >
              <span className="button-label">
                {submitting ? <LoadingSpinner size={16} /> : null}
                {submitting ? copy.submitBusy : copy.submitIdle}
              </span>
            </button>
            <Link to={copy.backTo} className="ghost-button">
              {copy.backLabel}
            </Link>
          </div>
        </form>
      </section>
    </div>
  );
}
