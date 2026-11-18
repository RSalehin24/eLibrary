import { twoFactorStatusLabel } from "./profileModel";

export function ProfileReadOnlyView({
  canSendToKindle,
  configuredKindleEmails,
  profile,
  roleLabel,
  twoFactor,
  visibleInitials,
  visibleName,
  visibleProfileImage
}) {
  return (
    <div className="profile-view-card">
      <div className="profile-summary">
        {visibleProfileImage ? (
          <img
            className="profile-avatar profile-avatar-large profile-summary-avatar"
            src={visibleProfileImage}
            alt={visibleName}
          />
        ) : (
          <div className="profile-avatar profile-avatar-large profile-summary-avatar">
            {visibleInitials}
          </div>
        )}
        <div className="profile-summary-meta">
          <h2>{visibleName}</h2>
          <p>{profile?.email}</p>
          <span className="status-pill">{roleLabel}</span>
        </div>
      </div>

      <div className="settings-list">
        <div className="settings-row">
          <span>Name</span>
          <strong>{profile?.full_name || "-"}</strong>
        </div>
        <div className="settings-row">
          <span>Email</span>
          <strong>{profile?.email}</strong>
        </div>
        <div className="settings-row">
          <span>Role</span>
          <strong>{roleLabel}</strong>
        </div>
        <div className="settings-row">
          <span>Two-Factor</span>
          <strong>{twoFactorStatusLabel(twoFactor)}</strong>
        </div>
        {canSendToKindle ? (
          <div className="settings-row">
            <span>Kindle Mails</span>
            {configuredKindleEmails.length ? (
              <strong className="profile-multi-line-value">
                {configuredKindleEmails.map((email) => (
                  <span key={email}>{email}</span>
                ))}
              </strong>
            ) : (
              <strong>Not set</strong>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
