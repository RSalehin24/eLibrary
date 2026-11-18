import LoadingSpinner from "./LoadingSpinner";

export default function TwoFactorSetupPanel({
  confirmLabel = "Verify and Enable",
  description = "",
  onCancel,
  onCopy,
  onSubmit,
  onTokenChange,
  required = false,
  setup,
  stacked = false,
  title = "Authenticator Setup",
  token,
  totpAction,
}) {
  return (
    <div
      className={
        stacked ? "totp-setup-panel totp-setup-panel-stacked" : "totp-setup-panel"
      }
    >
      <div className="panel-header">
        <div className="profile-section-heading">
          {title ? <h3>{title}</h3> : null}
          {description ? <p className="muted-copy">{description}</p> : null}
        </div>
        <div className="inline-pills">
          <button
            type="button"
            className="ghost-button"
            onClick={onCopy}
            disabled={Boolean(totpAction)}
          >
            Copy URL
          </button>
          {!required && onCancel ? (
            <button
              type="button"
              className="ghost-button"
              onClick={onCancel}
              disabled={Boolean(totpAction)}
            >
              <span className="button-label">
                {totpAction === "cancel" ? <LoadingSpinner size={14} /> : null}
                {totpAction === "cancel" ? "Canceling..." : "Cancel Setup"}
              </span>
            </button>
          ) : null}
        </div>
      </div>

      <div
        className={
          stacked ? "stack-form profile-setup-grid" : "two-column-layout profile-setup-grid"
        }
      >
        <div
          className="totp-qr-card"
          aria-label="Two-factor QR code"
          dangerouslySetInnerHTML={{ __html: setup.qr_svg }}
        />
        <div className="stack-form">
          <div className="settings-list">
            <span className="fact-label">Setup URL</span>
            <p className="mono-line">{setup.provisioning_uri}</p>
            <span className="fact-label">Secret</span>
            <p className="mono-line">{setup.secret}</p>
          </div>

          <form className="stack-form" onSubmit={onSubmit}>
            <label>
              <span className="fact-label">Verification Code</span>
              <input
                value={token}
                onChange={(event) => onTokenChange(event.target.value)}
                inputMode="numeric"
                placeholder="123456"
              />
            </label>
            <div className="inline-pills">
              <button
                type="submit"
                className="primary-button"
                disabled={Boolean(totpAction)}
              >
                <span className="button-label">
                  {totpAction === "verify" ? (
                    <LoadingSpinner size={14} />
                  ) : null}
                  {totpAction === "verify" ? "Verifying..." : confirmLabel}
                </span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
