import { useMemo } from "react";
import { getKindleEmailValidationState } from "../../utils/email";
import {
  initialsForUser,
  roleLabelForProfile,
  serializeKindleEmails
} from "./profileModel";

export function useProfileDerivedState({
  confirmNewPassword,
  currentPassword,
  fullName,
  kindleEmails,
  newPassword,
  profile,
  profileImageFile,
  profileImagePreview,
  removeProfileImage
}) {
  const visibleProfileImage = removeProfileImage
    ? ""
    : profileImagePreview || profile?.profile_image_url || "";
  const visibleName =
    fullName.trim() || profile?.full_name || profile?.email || "Profile";
  const visibleInitials = initialsForUser(visibleName);
  const roleLabel = roleLabelForProfile(profile);
  const kindleSenderEmail = profile?.kindle_sender_email || "the app sender email";
  const configuredKindleEmails = profile?.kindle_emails || [];
  const serializedKindleEmails = serializeKindleEmails(kindleEmails);
  const kindleEmailValidationStates = useMemo(
    () => kindleEmails.map((email) => getKindleEmailValidationState(email)),
    [kindleEmails]
  );
  const hasInvalidKindleEmail = kindleEmailValidationStates.some(
    (validationState) =>
      validationState.hasEmailInput && !validationState.emailLooksValid
  );
  const canAddKindleEmail =
    kindleEmailValidationStates.length > 0 &&
    kindleEmailValidationStates.every(
      (validationState) => validationState.emailLooksValid
    );
  const hasPasswordChanges = Boolean(
    currentPassword || newPassword || confirmNewPassword
  );
  const hasProfileChanges = useMemo(
    () =>
      fullName.trim() !== (profile?.full_name || "") ||
      Boolean(profileImageFile) ||
      removeProfileImage ||
      serializedKindleEmails !== (profile?.kindle_emails || []).join("\n") ||
      hasPasswordChanges,
    [
      fullName,
      profile?.full_name,
      profile?.kindle_emails,
      profileImageFile,
      removeProfileImage,
      serializedKindleEmails,
      hasPasswordChanges
    ]
  );

  return {
    canAddKindleEmail,
    configuredKindleEmails,
    hasInvalidKindleEmail,
    hasPasswordChanges,
    hasProfileChanges,
    kindleEmailValidationStates,
    kindleSenderEmail,
    roleLabel,
    serializedKindleEmails,
    visibleInitials,
    visibleName,
    visibleProfileImage
  };
}
