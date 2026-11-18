import { initialsForUser } from "./utils";

export function MenuIcon({ open = false }) {
  if (open) {
    return (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
      >
        <path d="M6 6l12 12M18 6 6 18" />
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
    >
      <path d="M4.5 7.5h15M4.5 12h15M4.5 16.5h15" />
    </svg>
  );
}

export function ChevronIcon({ open = false }) {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={open ? "M3.5 10 8 5.5 12.5 10" : "M3.5 6 8 10.5 12.5 6"} />
    </svg>
  );
}

export function MobileProfileSummary({ displayName, email, profileImageUrl }) {
  const label = displayName || email || "Account";

  return (
    <div className="mobile-nav-profile">
      {profileImageUrl ? (
        <img className="profile-avatar" src={profileImageUrl} alt={label} />
      ) : (
        <div className="profile-avatar">{initialsForUser(label)}</div>
      )}
      <div className="mobile-nav-profile-copy">
        <strong>{label}</strong>
        {email ? <span>{email}</span> : null}
      </div>
    </div>
  );
}
