import { getEmailValidationState } from "../utils/email";

function EmailFeedbackIcon({ valid }) {
  if (valid) {
    return (
      <svg
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M4.5 10.5 8 14l7.5-8.5" />
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m6 6 8 8" />
      <path d="m14 6-8 8" />
    </svg>
  );
}

export default function EmailInputFeedback({
  email,
  id,
  validationState,
  invalidMessage = "Enter a valid email address.",
  validMessage = "Email looks good.",
}) {
  const { hasEmailInput, emailLooksValid } =
    validationState ?? getEmailValidationState(email);

  if (!hasEmailInput) {
    return null;
  }

  return (
    <span
      id={id}
      className={`login-email-feedback login-email-feedback-${emailLooksValid ? "valid" : "invalid"}`}
      role="status"
      aria-live="polite"
    >
      <span className="login-email-feedback-icon" aria-hidden="true">
        <EmailFeedbackIcon valid={emailLooksValid} />
      </span>
      <span>{emailLooksValid ? validMessage : invalidMessage}</span>
    </span>
  );
}
