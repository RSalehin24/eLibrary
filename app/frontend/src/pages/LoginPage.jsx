import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import EmailInputFeedback from "../components/EmailInputFeedback";
import LoadingSpinner from "../components/LoadingSpinner";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSession } from "../hooks/useSession";
import { useToast } from "../hooks/useToast";
import { getEmailValidationState } from "../utils/email";
import { humanizeError } from "../utils/humanizeError";

export default function LoginPage() {
  usePageTitle("Sign in");
  const navigate = useNavigate();
  const { loading, authenticated, user, login } = useSession();

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
  const toast = useToast();
  const [phase, setPhase] = useState("credentials");
  const [form, setForm] = useState({ email: "", password: "", otp_token: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { normalizedEmail, hasEmailInput, emailLooksValid } =
    getEmailValidationState(form.email);
  const showEmailFeedback = phase === "credentials" && hasEmailInput;
  const credentialsReady =
    hasEmailInput && emailLooksValid && form.password.trim().length > 0;

  async function handleLogin(event) {
    event.preventDefault();
    if (submitting) {
      return;
    }
    if (!event.currentTarget.reportValidity()) {
      return;
    }
    if (phase === "credentials" && !credentialsReady) {
      return;
    }
    try {
      setSubmitting(true);
      const user = await login({
        ...form,
        email: normalizedEmail,
        otp_token: form.otp_token.trim(),
      });
      const requiresTotpSetup = Boolean(user?.totp_setup_required);
      toast.success(
        requiresTotpSetup
          ? "Signed in. Finish two-factor setup to continue."
          : "Signed in.",
      );
      const homePath = user?.is_superuser ? "/home" : "/my-books";
      navigate(requiresTotpSetup ? "/two-factor-setup" : homePath, {
        replace: true,
      });
    } catch (error) {
      const code = error?.payload?.code;
      if (code === "otp_required") {
        setPhase("otp");
        toast.info("Enter your authenticator code to continue.");
        return;
      }

      if (code === "otp_invalid") {
        setPhase("otp");
      }

      toast.error(humanizeError(error));
    } finally {
      setSubmitting(false);
    }
  }

  function resetPhase() {
    setPhase("credentials");
    setForm((current) => ({ ...current, otp_token: "" }));
  }

  return (
    <div className="login-shell">
      <section className={`detail-card login-card login-card-${phase}`}>
        <div className="login-header">
          <h1>{phase === "otp" ? "Verification" : "Sign in"}</h1>
        </div>
        <form className="stack-form" onSubmit={handleLogin}>
          <label>
            <span>Email</span>
            <input
              type="email"
              value={form.email}
              onChange={(event) =>
                setForm({ ...form, email: event.target.value })
              }
              inputMode="email"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              readOnly={phase === "otp"}
              required={phase === "credentials"}
              aria-describedby={
                showEmailFeedback ? "login-email-feedback" : undefined
              }
              aria-invalid={
                showEmailFeedback && !emailLooksValid ? "true" : undefined
              }
            />
            {showEmailFeedback ? (
              <EmailInputFeedback
                id="login-email-feedback"
                email={form.email}
              />
            ) : null}
          </label>
          <label>
            <span>Password</span>
            <div className="password-input-row">
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(event) =>
                  setForm({ ...form, password: event.target.value })
                }
                autoComplete="current-password"
                readOnly={phase === "otp"}
                required={phase === "credentials"}
              />
              <button
                type="button"
                className="password-visibility-button"
                onClick={() => setShowPassword((current) => !current)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                disabled={phase === "otp"}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          {phase === "otp" ? (
            <label className="login-otp-field">
              <span>TOTP code</span>
              <input
                type="text"
                value={form.otp_token}
                onChange={(event) =>
                  setForm({ ...form, otp_token: event.target.value })
                }
                autoFocus
                inputMode="numeric"
                placeholder="123456"
                required={phase === "otp"}
              />
            </label>
          ) : null}
          <div className="inline-pills login-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={
                submitting || (phase === "credentials" && !credentialsReady)
              }
            >
              <span className="button-label">
                {submitting ? <LoadingSpinner size={16} /> : null}
                {submitting
                  ? phase === "otp"
                    ? "Verifying..."
                    : "Signing in..."
                  : phase === "otp"
                    ? "Verify"
                    : "Continue"}
              </span>
            </button>
            {phase === "otp" ? (
              <button
                type="button"
                className="ghost-button"
                onClick={resetPhase}
                disabled={submitting}
              >
                Change account
              </button>
            ) : (
              <Link to="/reset-password" className="ghost-button">
                Reset password
              </Link>
            )}
          </div>
        </form>
      </section>
    </div>
  );
}
