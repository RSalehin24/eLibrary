import { KINDLE_EMAIL_INVALID_MESSAGE } from "../../utils/email";

export const emptyTotpSetup = {
  provisioning_uri: "",
  secret: "",
  qr_svg: ""
};

export function kindleEmailFieldsFromProfile(emails) {
  if (!Array.isArray(emails) || !emails.length) {
    return [""];
  }
  return emails.map((email) => String(email || ""));
}

export function serializeKindleEmails(emails) {
  if (!Array.isArray(emails)) {
    return "";
  }
  return emails
    .map((email) => String(email || "").trim())
    .filter(Boolean)
    .join("\n");
}

export function kindleEmailInvalidMessage(validationState) {
  if (validationState?.baseEmailLooksValid) {
    return KINDLE_EMAIL_INVALID_MESSAGE;
  }
  return "Enter a valid email address.";
}

export function initialsForUser(value) {
  return (
    (value || "")
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || "")
      .join("") || "?"
  );
}

export function roleLabelForProfile(profile) {
  if (profile?.is_superuser) {
    return "Super Admin";
  }
  if (profile?.is_staff) {
    return "Staff";
  }
  return "User";
}

export function twoFactorStatusLabel(twoFactor) {
  if (twoFactor.enabled) {
    return "Set up";
  }
  return "Not set up";
}
