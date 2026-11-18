import LoadingSpinner from "../../components/LoadingSpinner";
import TwoFactorSetupPanel from "../../components/TwoFactorSetupPanel";
import { twoFactorStatusLabel } from "./profileModel";

export function ProfileSecurityPanel({
  cancelSetup,
  confirmSetup,
  copyProvisioningUrl,
  disableTotp,
  openSetup,
  setSetupVisible,
  setToken,
  setup,
  setupVisible,
  token,
  totpAction,
  totpFeedback,
  twoFactor
}) {
  const statusLabel = twoFactorStatusLabel(twoFactor);

  return (
    <section className="detail-main">
      <div className="panel-header">
        <div className="profile-section-heading">
          <h2>Two-Factor Authentication</h2>
        </div>
        <span
          className={`status-pill ${
            twoFactor.enabled ? "status-ready" : "status-needs_review"
          }`}
        >
          {statusLabel}
        </span>
      </div>

      <div className="profile-security-grid">
        <div className="settings-list">
          <div className="settings-row">
            <span>Status</span>
            <strong>{statusLabel}</strong>
          </div>
          <div className="settings-row">
            <span>Requirement</span>
            <strong>{twoFactor.required ? "Required by admin" : "Optional"}</strong>
          </div>
          <div className="settings-row">
            <span>Method</span>
            <strong>
              {twoFactor.enabled ? "Authenticator app" : "Not configured"}
            </strong>
          </div>
        </div>
      </div>

      <div className="inline-pills">
        {!twoFactor.enabled ? (
          <button
            type="button"
            className="primary-button"
            onClick={setupVisible ? () => setSetupVisible(false) : openSetup}
            disabled={Boolean(totpAction)}
          >
            <span className="button-label">
              {totpAction === "setup" ? <LoadingSpinner size={14} /> : null}
              {totpAction === "setup"
                ? "Preparing..."
                : setupVisible
                  ? "Hide Setup"
                  : "Setup Authenticator"}
            </span>
          </button>
        ) : null}
        {twoFactor.enabled && !twoFactor.required ? (
          <button
            type="button"
            className="ghost-button"
            onClick={disableTotp}
            disabled={Boolean(totpAction)}
          >
            <span className="button-label">
              {totpAction === "disable" ? <LoadingSpinner size={14} /> : null}
              {totpAction === "disable" ? "Turning off..." : "Turn Off"}
            </span>
          </button>
        ) : null}
      </div>

      {totpFeedback ? <p className="form-feedback">{totpFeedback}</p> : null}

      {setupVisible && setup.provisioning_uri ? (
        <TwoFactorSetupPanel
          onCancel={cancelSetup}
          onCopy={copyProvisioningUrl}
          onSubmit={confirmSetup}
          onTokenChange={setToken}
          setup={setup}
          token={token}
          totpAction={totpAction}
        />
      ) : null}
    </section>
  );
}
