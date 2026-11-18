export function ProfileIdentityEditor({
  clearProfileImage,
  fullName,
  handleProfileImageChange,
  profile,
  setFullName,
  visibleInitials,
  visibleName,
  visibleProfileImage
}) {
  return (
    <div className="profile-editor-card">
      <div className="profile-media-panel">
        <div className="profile-photo-stack">
          <div className="profile-photo-frame">
            {visibleProfileImage ? (
              <img
                className="profile-avatar profile-avatar-large"
                src={visibleProfileImage}
                alt={visibleName}
              />
            ) : (
              <div className="profile-avatar profile-avatar-large">
                {visibleInitials}
              </div>
            )}
            <label
              className="profile-photo-upload"
              aria-label="Upload profile photo"
              title="Upload profile photo"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M12 5a1 1 0 0 1 1 1v5h5a1 1 0 1 1 0 2h-5v5a1 1 0 1 1-2 0v-5H6a1 1 0 1 1 0-2h5V6a1 1 0 0 1 1-1Z"
                  fill="currentColor"
                />
              </svg>
              <span className="sr-only">Upload profile photo</span>
              <input
                className="profile-upload-input"
                type="file"
                accept="image/*"
                onChange={handleProfileImageChange}
              />
            </label>
          </div>
          {visibleProfileImage ? (
            <button
              type="button"
              className="ghost-button profile-photo-remove"
              onClick={clearProfileImage}
            >
              Remove Photo
            </button>
          ) : null}
        </div>
      </div>

      <div className="detail-facts profile-form-grid">
        <label>
          <span className="fact-label">Name</span>
          <input
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            placeholder="Your name"
          />
        </label>
        <label>
          <span className="fact-label">Email</span>
          <input value={profile?.email || ""} readOnly disabled />
        </label>
      </div>
    </div>
  );
}
