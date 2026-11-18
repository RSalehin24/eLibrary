import { authApi } from "../../api/client";
import { getKindleEmailValidationState } from "../../utils/email";
import { kindleEmailInvalidMessage, serializeKindleEmails } from "./profileModel";

export async function saveProfileChanges({
  confirmNewPassword,
  currentPassword,
  fullName,
  hasPasswordChanges,
  kindleEmails,
  newPassword,
  profileImageFile,
  refreshSession,
  removeProfileImage,
  resetProfileEditor,
  setIsEditing,
  setProfile,
  toast
}) {
  const firstInvalidKindleEmail = kindleEmails
    .map((email) => getKindleEmailValidationState(email))
    .find(
      (validationState) =>
        validationState.hasEmailInput && !validationState.emailLooksValid
    );

  if (hasPasswordChanges && !currentPassword) {
    toast.error("Enter your current password to change it.");
    return;
  }
  if (hasPasswordChanges && !newPassword) {
    toast.error("Enter a new password.");
    return;
  }
  if (hasPasswordChanges && newPassword !== confirmNewPassword) {
    toast.error("The new password fields must match.");
    return;
  }
  if (firstInvalidKindleEmail) {
    toast.error(kindleEmailInvalidMessage(firstInvalidKindleEmail));
    return;
  }

  const body = new FormData();
  body.append("full_name", fullName.trim());
  if (profileImageFile) {
    body.append("profile_image", profileImageFile);
  }
  if (removeProfileImage) {
    body.append("remove_profile_image", "true");
  }
  body.append("kindle_emails_text", serializeKindleEmails(kindleEmails));
  if (hasPasswordChanges) {
    body.append("current_password", currentPassword);
    body.append("new_password", newPassword);
    body.append("confirm_new_password", confirmNewPassword);
  }

  const payload = await authApi.updateProfile(body);
  setProfile(payload);
  resetProfileEditor(payload);
  await refreshSession();
  setIsEditing(false);
  toast.success("Profile updated.");
}
