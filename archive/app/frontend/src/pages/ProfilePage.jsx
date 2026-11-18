import { useEffect, useState } from "react";
import { authApi } from "../api/client";
import PageLoader from "../components/PageLoader";
import { ProfileEditorForm } from "../features/profile/ProfileEditorForm";
import { ProfileReadOnlyView } from "../features/profile/ProfileReadOnlyView";
import { ProfileSecurityPanel } from "../features/profile/ProfileSecurityPanel";
import { saveProfileChanges } from "../features/profile/profileSaveAction";
import {
  emptyTotpSetup,
  kindleEmailFieldsFromProfile,
} from "../features/profile/profileModel";
import { useProfileDerivedState } from "../features/profile/useProfileDerivedState";
import { useProfileTwoFactorActions } from "../features/profile/useProfileTwoFactorActions";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSession } from "../hooks/useSession";
import { useToast } from "../hooks/useToast";
import { hasCapability } from "../utils/capabilities";
import { humanizeError } from "../utils/humanizeError";

export default function ProfilePage() {
  usePageTitle("Profile");
  const { user, refreshSession } = useSession();
  const toast = useToast();
  const canSendToKindle = hasCapability(user, "send:kindle");
  const [profile, setProfile] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [twoFactor, setTwoFactor] = useState({
    enabled: false,
    pending_setup: false,
    required: false,
    setup_required: false,
  });
  const [fullName, setFullName] = useState("");
  const [setup, setSetup] = useState(emptyTotpSetup);
  const [setupVisible, setSetupVisible] = useState(false);
  const [token, setToken] = useState("");
  const [profileImageFile, setProfileImageFile] = useState(null);
  const [profileImagePreview, setProfileImagePreview] = useState("");
  const [removeProfileImage, setRemoveProfileImage] = useState(false);
  const [kindleEmails, setKindleEmails] = useState([""]);
  const [kindleSectionOpen, setKindleSectionOpen] = useState(false);
  const [passwordSectionOpen, setPasswordSectionOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmNewPassword, setShowConfirmNewPassword] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [loading, setLoading] = useState(true);
  const [totpAction, setTotpAction] = useState("");
  const [totpFeedback, setTotpFeedback] = useState("");
  const derived = useProfileDerivedState({
    confirmNewPassword,
    currentPassword,
    fullName,
    kindleEmails,
    newPassword,
    profile,
    profileImageFile,
    profileImagePreview,
    removeProfileImage,
  });

  async function loadProfile(options = {}) {
    const { preserveEditor = false } = options;
    try {
      setLoading(true);
      const [profilePayload, statusPayload] = await Promise.all([
        authApi.profile(),
        authApi.twoFactorStatus(),
      ]);
      setProfile(profilePayload);
      if (!preserveEditor) {
        resetProfileEditor(profilePayload);
      }
      setTwoFactor(statusPayload);
    } catch (error) {
      toast.error(humanizeError(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProfile();
  }, [user?.id]);

  function resetProfileEditor(sourceProfile = profile) {
    setFullName(sourceProfile?.full_name || "");
    setProfileImageFile(null);
    setProfileImagePreview(sourceProfile?.profile_image_url || "");
    setRemoveProfileImage(false);
    setKindleEmails(
      kindleEmailFieldsFromProfile(sourceProfile?.kindle_emails || []),
    );
    setKindleSectionOpen(false);
    setPasswordSectionOpen(false);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmNewPassword("");
    setShowCurrentPassword(false);
    setShowNewPassword(false);
    setShowConfirmNewPassword(false);
    setSetupVisible(false);
    setTotpFeedback("");
    setToken("");
  }

  function startEditing() {
    resetProfileEditor(profile);
    setIsEditing(true);
  }

  function stopEditing() {
    resetProfileEditor(profile);
    setIsEditing(false);
  }

  function updateKindleEmail(index, value) {
    setKindleEmails((current) =>
      current.map((email, currentIndex) =>
        currentIndex === index ? value : email,
      ),
    );
  }

  function addKindleEmailField() {
    setKindleEmails((current) => [...current, ""]);
  }

  function removeKindleEmailField(index) {
    setKindleEmails((current) => {
      const next = current.filter((_, currentIndex) => currentIndex !== index);
      return next.length ? next : [""];
    });
  }

  async function saveProfile(event) {
    event.preventDefault();
    try {
      setSavingProfile(true);
      await saveProfileChanges({
        confirmNewPassword,
        currentPassword,
        fullName,
        hasPasswordChanges: derived.hasPasswordChanges,
        kindleEmails,
        newPassword,
        profileImageFile,
        refreshSession,
        removeProfileImage,
        resetProfileEditor,
        setIsEditing,
        setProfile,
        toast,
      });
    } catch (error) {
      toast.error(humanizeError(error));
    } finally {
      setSavingProfile(false);
    }
  }

  function handleProfileImageChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setProfileImageFile(file);
    setProfileImagePreview(URL.createObjectURL(file));
    setRemoveProfileImage(false);
  }

  function clearProfileImage() {
    setProfileImageFile(null);
    setProfileImagePreview("");
    setRemoveProfileImage(true);
  }

  const {
    cancelSetup,
    confirmSetup,
    copyProvisioningUrl,
    disableTotp,
    openSetup,
  } = useProfileTwoFactorActions({
    loadProfile,
    refreshSession,
    setSetup,
    setSetupVisible,
    setToken,
    setTotpAction,
    setTotpFeedback,
    setTwoFactor,
    setup,
    toast,
    token,
    totpAction,
  });

  if (loading) {
    return (
      <PageLoader
        label="Loading profile"
        detail="Fetching your account settings and security status."
        variant="profile"
      />
    );
  }

  return (
    <div className="page-stack">
      <section className="detail-card profile-shell">
        <div className="panel-header profile-header-bar">
          <h1>Profile</h1>
          <button
            type="button"
            className="ghost-button"
            onClick={isEditing ? stopEditing : startEditing}
          >
            {isEditing ? "Cancel" : "Edit"}
          </button>
        </div>

        {!isEditing ? (
          <ProfileReadOnlyView
            canSendToKindle={canSendToKindle}
            configuredKindleEmails={derived.configuredKindleEmails}
            profile={profile}
            roleLabel={derived.roleLabel}
            twoFactor={twoFactor}
            visibleInitials={derived.visibleInitials}
            visibleName={derived.visibleName}
            visibleProfileImage={derived.visibleProfileImage}
          />
        ) : (
          <div className="page-stack">
            <ProfileEditorForm
              addKindleEmailField={addKindleEmailField}
              canAddKindleEmail={derived.canAddKindleEmail}
              canSendToKindle={canSendToKindle}
              clearProfileImage={clearProfileImage}
              confirmNewPassword={confirmNewPassword}
              currentPassword={currentPassword}
              fullName={fullName}
              handleProfileImageChange={handleProfileImageChange}
              hasInvalidKindleEmail={derived.hasInvalidKindleEmail}
              hasProfileChanges={derived.hasProfileChanges}
              kindleEmailValidationStates={derived.kindleEmailValidationStates}
              kindleEmails={kindleEmails}
              kindleSectionOpen={kindleSectionOpen}
              kindleSenderEmail={derived.kindleSenderEmail}
              newPassword={newPassword}
              onSave={saveProfile}
              passwordSectionOpen={passwordSectionOpen}
              profile={profile}
              removeKindleEmailField={removeKindleEmailField}
              savingProfile={savingProfile}
              setConfirmNewPassword={setConfirmNewPassword}
              setCurrentPassword={setCurrentPassword}
              setFullName={setFullName}
              setKindleSectionOpen={setKindleSectionOpen}
              setNewPassword={setNewPassword}
              setPasswordSectionOpen={setPasswordSectionOpen}
              setShowConfirmNewPassword={setShowConfirmNewPassword}
              setShowCurrentPassword={setShowCurrentPassword}
              setShowNewPassword={setShowNewPassword}
              showConfirmNewPassword={showConfirmNewPassword}
              showCurrentPassword={showCurrentPassword}
              showNewPassword={showNewPassword}
              updateKindleEmail={updateKindleEmail}
              visibleInitials={derived.visibleInitials}
              visibleName={derived.visibleName}
              visibleProfileImage={derived.visibleProfileImage}
            />
            <ProfileSecurityPanel
              cancelSetup={cancelSetup}
              confirmSetup={confirmSetup}
              copyProvisioningUrl={copyProvisioningUrl}
              disableTotp={disableTotp}
              openSetup={openSetup}
              setSetupVisible={setSetupVisible}
              setToken={setToken}
              setup={setup}
              setupVisible={setupVisible}
              token={token}
              totpAction={totpAction}
              totpFeedback={totpFeedback}
              twoFactor={twoFactor}
            />
          </div>
        )}
      </section>
    </div>
  );
}
