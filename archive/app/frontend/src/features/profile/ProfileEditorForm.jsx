import { ProfileIdentityEditor } from "./ProfileIdentityEditor";
import { ProfileKindleEditor } from "./ProfileKindleEditor";
import { ProfilePasswordEditor } from "./ProfilePasswordEditor";

export function ProfileEditorForm({
  canAddKindleEmail,
  canSendToKindle,
  clearProfileImage,
  confirmNewPassword,
  currentPassword,
  fullName,
  handleProfileImageChange,
  hasInvalidKindleEmail,
  hasProfileChanges,
  kindleEmailValidationStates,
  kindleEmails,
  kindleSectionOpen,
  kindleSenderEmail,
  newPassword,
  onSave,
  passwordSectionOpen,
  profile,
  removeKindleEmailField,
  savingProfile,
  setConfirmNewPassword,
  setCurrentPassword,
  setFullName,
  setKindleSectionOpen,
  setNewPassword,
  setPasswordSectionOpen,
  setShowConfirmNewPassword,
  setShowCurrentPassword,
  setShowNewPassword,
  showConfirmNewPassword,
  showCurrentPassword,
  showNewPassword,
  updateKindleEmail,
  visibleInitials,
  visibleName,
  visibleProfileImage,
  addKindleEmailField
}) {
  return (
    <form className="stack-form" onSubmit={onSave}>
      <ProfileIdentityEditor
        clearProfileImage={clearProfileImage}
        fullName={fullName}
        handleProfileImageChange={handleProfileImageChange}
        profile={profile}
        setFullName={setFullName}
        visibleInitials={visibleInitials}
        visibleName={visibleName}
        visibleProfileImage={visibleProfileImage}
      />
      <ProfilePasswordEditor
        confirmNewPassword={confirmNewPassword}
        currentPassword={currentPassword}
        newPassword={newPassword}
        passwordSectionOpen={passwordSectionOpen}
        setConfirmNewPassword={setConfirmNewPassword}
        setCurrentPassword={setCurrentPassword}
        setNewPassword={setNewPassword}
        setPasswordSectionOpen={setPasswordSectionOpen}
        setShowConfirmNewPassword={setShowConfirmNewPassword}
        setShowCurrentPassword={setShowCurrentPassword}
        setShowNewPassword={setShowNewPassword}
        showConfirmNewPassword={showConfirmNewPassword}
        showCurrentPassword={showCurrentPassword}
        showNewPassword={showNewPassword}
      />
      {canSendToKindle ? (
        <ProfileKindleEditor
          addKindleEmailField={addKindleEmailField}
          canAddKindleEmail={canAddKindleEmail}
          kindleEmailValidationStates={kindleEmailValidationStates}
          kindleEmails={kindleEmails}
          kindleSectionOpen={kindleSectionOpen}
          kindleSenderEmail={kindleSenderEmail}
          removeKindleEmailField={removeKindleEmailField}
          setKindleSectionOpen={setKindleSectionOpen}
          updateKindleEmail={updateKindleEmail}
        />
      ) : null}
      <div className="profile-save-bar">
        <button
          type="submit"
          className="primary-button"
          disabled={savingProfile || !hasProfileChanges || hasInvalidKindleEmail}
        >
          {savingProfile ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </form>
  );
}
