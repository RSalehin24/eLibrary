function PasswordField({
  autoComplete,
  label,
  onChange,
  onToggle,
  placeholder,
  show,
  value
}) {
  return (
    <label className={label === "Current Password" ? "field-span-full" : ""}>
      <span className="fact-label">{label}</span>
      <div className="password-input-row">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete={autoComplete}
          placeholder={placeholder}
        />
        <button
          type="button"
          className="password-visibility-button"
          onClick={onToggle}
          aria-label={show ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
        >
          {show ? "Hide" : "Show"}
        </button>
      </div>
    </label>
  );
}

export function ProfilePasswordEditor({
  confirmNewPassword,
  currentPassword,
  newPassword,
  passwordSectionOpen,
  setConfirmNewPassword,
  setCurrentPassword,
  setNewPassword,
  setPasswordSectionOpen,
  setShowConfirmNewPassword,
  setShowCurrentPassword,
  setShowNewPassword,
  showConfirmNewPassword,
  showCurrentPassword,
  showNewPassword
}) {
  return (
    <section className="detail-main profile-password-card">
      <div className="panel-header">
        <div className="profile-section-heading">
          <h2>Change Password</h2>
        </div>
        <button
          type="button"
          className="ghost-button"
          onClick={() => setPasswordSectionOpen((current) => !current)}
        >
          {passwordSectionOpen ? "Hide" : "Expand"}
        </button>
      </div>

      {passwordSectionOpen ? (
        <div className="profile-password-panel">
          <div className="profile-password-grid">
            <PasswordField
              autoComplete="current-password"
              label="Current Password"
              onChange={setCurrentPassword}
              onToggle={() => setShowCurrentPassword((current) => !current)}
              placeholder="Current password"
              show={showCurrentPassword}
              value={currentPassword}
            />
            <PasswordField
              autoComplete="new-password"
              label="New Password"
              onChange={setNewPassword}
              onToggle={() => setShowNewPassword((current) => !current)}
              placeholder="New password"
              show={showNewPassword}
              value={newPassword}
            />
            <PasswordField
              autoComplete="new-password"
              label="Confirm New Password"
              onChange={setConfirmNewPassword}
              onToggle={() => setShowConfirmNewPassword((current) => !current)}
              placeholder="Confirm new password"
              show={showConfirmNewPassword}
              value={confirmNewPassword}
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
