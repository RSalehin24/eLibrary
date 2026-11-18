export const PASSWORD_LINK_COPY = {
  create: {
    backTo: "/login",
    backLabel: "Back",
    invalidMessage:
      "Invalid account setup link. Ask your administrator to send a new invite.",
    invalidHeading: "The link has been expired",
    eyebrow: "Account setup",
    heading: "Create password",
    submitIdle: "Create password",
    submitBusy: "Saving...",
    successMessage: "Password created. Please sign in.",
    totpSetupMessage:
      "Password created. Set up two-factor authentication to continue."
  },
  reset: {
    backTo: "/reset-password",
    backLabel: "Back",
    invalidHeading: "The link has expired",
    invalidMessage: "Invalid reset link. Request a new password reset email.",
    eyebrow: "Password reset",
    heading: "New password",
    submitIdle: "Reset password",
    submitBusy: "Resetting...",
    successMessage: "Password reset complete. Please sign in.",
    totpSetupMessage:
      "Password reset. Set up two-factor authentication to continue."
  }
};
