import { useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { authApi } from "../api/client";
import EmailInputFeedback from "../components/EmailInputFeedback";
import LoadingSpinner from "../components/LoadingSpinner";
import { usePageTitle } from "../hooks/usePageTitle";
import { useToast } from "../hooks/useToast";
import { getEmailValidationState } from "../utils/email";
import { humanizeError } from "../utils/humanizeError";

export default function PasswordResetPage() {
  usePageTitle("Reset password");
  const [params] = useSearchParams();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { normalizedEmail, hasEmailInput, emailLooksValid } =
    getEmailValidationState(email);

  const uid = params.get("uid") || "";
  const token = params.get("token") || "";
  if (uid && token) {
    return (
      <Navigate
        to={`/reset-password/confirm?uid=${encodeURIComponent(uid)}&token=${encodeURIComponent(token)}`}
        replace
      />
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) {
      return;
    }
    if (!event.currentTarget.reportValidity() || !emailLooksValid) {
      return;
    }

    try {
      setSubmitting(true);
      const response = await authApi.passwordReset({ email: normalizedEmail });
      toast.success(response?.detail || "Reset email has been sent.");
    } catch (error) {
      toast.error(humanizeError(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-shell">
      <section className="detail-card login-card auth-request-card">
        <p className="eyebrow">Password reset</p>
        <h1>Reset your password</h1>
        <form className="stack-form" onSubmit={handleSubmit}>
          <label>
            <input
              type="email"
              aria-label="Email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              inputMode="email"
              autoComplete="email"
              autoCapitalize="none"
              spellCheck={false}
              placeholder="you@example.com"
              required
              aria-describedby={
                hasEmailInput ? "password-reset-email-feedback" : undefined
              }
              aria-invalid={
                hasEmailInput && !emailLooksValid ? "true" : undefined
              }
            />
            <EmailInputFeedback
              id="password-reset-email-feedback"
              email={email}
            />
          </label>
          <div className="inline-pills login-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={!hasEmailInput || !emailLooksValid || submitting}
            >
              <span className="button-label">
                {submitting ? <LoadingSpinner size={16} /> : null}
                {submitting ? "Sending..." : "Reset Password"}
              </span>
            </button>
            <Link to="/login" className="ghost-button">
              Back
            </Link>
          </div>
        </form>
      </section>
    </div>
  );
}
