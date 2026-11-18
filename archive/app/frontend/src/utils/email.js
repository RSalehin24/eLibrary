export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const KINDLE_EMAIL_DOMAINS = new Set(["kindle.com"]);
export const KINDLE_EMAIL_INVALID_MESSAGE =
  "Use a Kindle email ending in @kindle.com.";

export function normalizeEmail(value) {
  return typeof value === "string" ? value.trim() : "";
}

export function isValidEmail(value) {
  return EMAIL_PATTERN.test(normalizeEmail(value));
}

export function getEmailValidationState(value) {
  const normalizedEmail = normalizeEmail(value);

  return {
    normalizedEmail,
    hasEmailInput: normalizedEmail.length > 0,
    emailLooksValid: EMAIL_PATTERN.test(normalizedEmail),
  };
}

export function isValidKindleEmail(value) {
  const { normalizedEmail, emailLooksValid } = getEmailValidationState(value);
  if (!emailLooksValid) {
    return false;
  }
  const [, domain = ""] = normalizedEmail.split("@");
  return KINDLE_EMAIL_DOMAINS.has(domain.toLowerCase());
}

export function getKindleEmailValidationState(value) {
  const baseState = getEmailValidationState(value);
  const kindleDomainLooksValid = isValidKindleEmail(baseState.normalizedEmail);

  return {
    ...baseState,
    baseEmailLooksValid: baseState.emailLooksValid,
    kindleDomainLooksValid,
    emailLooksValid: kindleDomainLooksValid,
  };
}
