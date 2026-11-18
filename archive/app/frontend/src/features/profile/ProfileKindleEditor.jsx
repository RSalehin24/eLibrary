import EmailInputFeedback from "../../components/EmailInputFeedback";
import { kindleEmailInvalidMessage } from "./profileModel";

export function ProfileKindleEditor({
  addKindleEmailField,
  canAddKindleEmail,
  kindleEmailValidationStates,
  kindleEmails,
  kindleSectionOpen,
  kindleSenderEmail,
  removeKindleEmailField,
  setKindleSectionOpen,
  updateKindleEmail
}) {
  return (
    <section className="detail-main profile-password-card">
      <div className="panel-header">
        <div className="profile-section-heading">
          <h2>Kindle Mails</h2>
        </div>
        <button
          type="button"
          className="ghost-button"
          onClick={() => setKindleSectionOpen((current) => !current)}
        >
          {kindleSectionOpen ? "Hide" : "Expand"}
        </button>
      </div>

      {kindleSectionOpen ? (
        <div className="profile-password-panel">
          <p className="form-helper-text">
            <p className="profile-kindle-info-margin">
              {" "}
              &gt; Allow <strong>{kindleSenderEmail}</strong> in{" "}
              <i>
                Manage Your Content and Devices &gt; Preferences &gt; Personal
                Document Settings
              </i>{" "}
              in your Amazon settings.
            </p>
            <p>
              {" "}
              &gt; For adding multiple emails please ensure{" "}
              <strong>Personal Document Archiving</strong> is disabled.
            </p>
          </p>
          <div className="profile-kindle-email-list">
            {kindleEmails.map((email, index) => {
              const validationState = kindleEmailValidationStates[index];

              return (
                <div
                  key={`kindle-email-${index}`}
                  className="profile-kindle-email-row"
                >
                  <div className="profile-kindle-email-field">
                    <input
                      type="email"
                      value={email}
                      onChange={(event) => updateKindleEmail(index, event.target.value)}
                      inputMode="email"
                      autoCapitalize="none"
                      spellCheck={false}
                      placeholder="yourname@kindle.com"
                      aria-label={`Kindle Email ${index + 1}`}
                      aria-describedby={
                        validationState?.hasEmailInput
                          ? `profile-kindle-email-feedback-${index}`
                          : undefined
                      }
                      aria-invalid={
                        validationState?.hasEmailInput &&
                        !validationState.emailLooksValid
                          ? "true"
                          : undefined
                      }
                    />
                    {validationState?.hasEmailInput ? (
                      <EmailInputFeedback
                        id={`profile-kindle-email-feedback-${index}`}
                        validationState={validationState}
                        invalidMessage={kindleEmailInvalidMessage(validationState)}
                        validMessage="Kindle email looks good."
                      />
                    ) : null}
                  </div>
                  {kindleEmails.length > 1 ? (
                    <button
                      type="button"
                      className="icon-button danger-button profile-kindle-email-delete"
                      onClick={() => removeKindleEmailField(index)}
                      aria-label={`Delete email ${index + 1}`}
                      title={`Delete email ${index + 1}`}
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path
                          d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 7h2v7h-2v-7Zm4 0h2v7h-2v-7ZM7 10h2v7H7v-7Zm-1 10h12l1-13H5l1 13Z"
                          fill="currentColor"
                        />
                      </svg>
                    </button>
                  ) : null}
                </div>
              );
            })}
          </div>
          <div className="profile-kindle-email-actions">
            <button
              type="button"
              className="icon-button profile-kindle-email-add"
              onClick={addKindleEmailField}
              disabled={!canAddKindleEmail}
              aria-label="Add Kindle Email"
              title="Add Kindle Email"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M12 5v14M5 12h14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
