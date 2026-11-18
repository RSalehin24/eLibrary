import EmailInputFeedback from "../../../components/EmailInputFeedback";
import LoadingSpinner from "../../../components/LoadingSpinner";
import { getEmailValidationState } from "../../../utils/email";

export default function AccessUserEditorCard({
  accountScopes,
  editingUserId,
  isEditingUser,
  onCancel,
  onClearPermissions,
  onCopyPasswordValue,
  onSelectAllPermissions,
  onSetShowCreateUserPassword,
  onSetUserForm,
  onSubmit,
  onSuggestPassword,
  onToggleUserScope,
  showCreateUserPassword,
  submittingUser,
  userEditorRef,
  userForm,
}) {
  const { hasEmailInput, emailLooksValid } = getEmailValidationState(
    userForm.email,
  );
  const showCreateUserEmailFeedback = !isEditingUser && hasEmailInput;
  const hasValidCreateUserEmail =
    isEditingUser || (hasEmailInput && emailLooksValid);

  return (
    <section className="detail-card" data-testid="access-user-editor">
      <div ref={userEditorRef} className="access-user-editor-anchor" />
      <div className="panel-header">
        <h2>{editingUserId ? "Edit User" : "Create User"}</h2>
        {editingUserId ? (
          <button
            type="button"
            className="ghost-button"
            onClick={onCancel}
            disabled={submittingUser}
          >
            Cancel
          </button>
        ) : null}
      </div>

      <form className="stack-form" onSubmit={onSubmit} data-testid="access-user-form">
        <fieldset className="form-fieldset-reset" disabled={submittingUser}>
          <div className="detail-facts access-user-editor-primary-row">
            <label>
              <span className="fact-label">Name</span>
              <input
                value={userForm.full_name}
                onChange={(event) =>
                  onSetUserForm({
                    ...userForm,
                    full_name: event.target.value,
                  })
                }
                placeholder="Full name"
                disabled={isEditingUser}
                readOnly={isEditingUser}
              />
            </label>
            <label className="access-user-email-field">
              <span className="fact-label">Email</span>
              <input
                type="email"
                value={userForm.email}
                onChange={(event) =>
                  onSetUserForm({ ...userForm, email: event.target.value })
                }
                inputMode="email"
                autoComplete="email"
                autoCapitalize="none"
                spellCheck={false}
                placeholder="Email address"
                required={!isEditingUser}
                disabled={isEditingUser}
                readOnly={isEditingUser}
                aria-describedby={
                  showCreateUserEmailFeedback
                    ? "access-user-email-feedback"
                    : undefined
                }
                aria-invalid={
                  showCreateUserEmailFeedback && !emailLooksValid
                    ? "true"
                    : undefined
                }
              />
              {showCreateUserEmailFeedback ? (
                <EmailInputFeedback
                  id="access-user-email-feedback"
                  email={userForm.email}
                />
              ) : null}
            </label>
            <label>
              <div className="field-header access-password-header">
                <span className="fact-label">Password Setup</span>
                {!isEditingUser && !userForm.send_invite_email ? (
                  <div className="field-header-actions">
                    <button
                      type="button"
                      className="icon-button"
                      onClick={() => void onSuggestPassword()}
                      aria-label="Generate new password"
                      title="Generate new password"
                    >
                      ↻
                    </button>
                    <button
                      type="button"
                      className="icon-button"
                      onClick={() => void onCopyPasswordValue(userForm.password)}
                      aria-label="Copy password"
                      title="Copy password"
                    >
                      ⧉
                    </button>
                  </div>
                ) : null}
              </div>
              {isEditingUser ? (
                <input
                  type="password"
                  value=""
                  placeholder="Password changes are disabled here"
                  disabled
                  readOnly
                />
              ) : userForm.send_invite_email ? (
                <p className="muted-copy access-invite-note">
                  A setup email with a password-reset link will be sent after
                  the account is created.
                </p>
              ) : (
                <div className="password-input-row">
                  <input
                    type={showCreateUserPassword ? "text" : "password"}
                    value={userForm.password}
                    onChange={(event) =>
                      onSetUserForm({
                        ...userForm,
                        password: event.target.value,
                      })
                    }
                    placeholder="Create password"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="password-visibility-button"
                    onClick={() =>
                      onSetShowCreateUserPassword((current) => !current)
                    }
                    aria-label={
                      showCreateUserPassword
                        ? "Hide create password"
                        : "Show create password"
                    }
                  >
                    {showCreateUserPassword ? "Hide" : "Show"}
                  </button>
                </div>
              )}
            </label>
          </div>

          <div className="settings-list">
            <span className="fact-label">Account Settings</span>
            <div className="settings-options-grid">
              {!isEditingUser ? (
                <label className="setting-option-card">
                  <div className="setting-option-copy">
                    <strong>Send Setup Email</strong>
                    <span>
                      Send a reset link so the user can choose their own
                      password.
                    </span>
                  </div>
                  <input
                    type="checkbox"
                    checked={userForm.send_invite_email}
                    onChange={(event) =>
                      onSetUserForm({
                        ...userForm,
                        send_invite_email: event.target.checked,
                        password: event.target.checked ? "" : userForm.password,
                      })
                    }
                  />
                </label>
              ) : null}
              <label className="setting-option-card">
                <div className="setting-option-copy">
                  <strong>Active Account</strong>
                  <span>Allow this user to sign in and use the workspace.</span>
                </div>
                <input
                  type="checkbox"
                  checked={userForm.is_active}
                  onChange={(event) =>
                    onSetUserForm({
                      ...userForm,
                      is_active: event.target.checked,
                    })
                  }
                />
              </label>
              <label className="setting-option-card">
                <div className="setting-option-copy">
                  <strong>Require Two-Factor</strong>
                  <span>
                    Require authenticator setup before the user can continue.
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={userForm.totp_required}
                  onChange={(event) =>
                    onSetUserForm({
                      ...userForm,
                      totp_required: event.target.checked,
                    })
                  }
                />
              </label>
            </div>
          </div>

          <div className="settings-list">
            <span className="fact-label">Account Permissions</span>
            <div className="inline-pills">
              <button
                type="button"
                className="ghost-button"
                onClick={onSelectAllPermissions}
              >
                All Permissions
              </button>
              <button
                type="button"
                className="ghost-button"
                onClick={onClearPermissions}
              >
                Clear
              </button>
            </div>
            {accountScopes.length ? (
              <div className="scope-grid">
                {accountScopes.map((scope) => (
                  <label key={scope.value} className="scope-card">
                    <input
                      type="checkbox"
                      checked={userForm.global_scopes.includes(scope.value)}
                      onChange={() => onToggleUserScope(scope.value)}
                    />
                    <span>{scope.label}</span>
                  </label>
                ))}
              </div>
            ) : (
              <p className="muted-copy">No account permissions are available.</p>
            )}
          </div>

          <div className="inline-pills access-user-submit-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={submittingUser || !hasValidCreateUserEmail}
            >
              {submittingUser ? (
                <span className="button-label">
                  <LoadingSpinner size={14} />
                  {editingUserId ? "Saving..." : "Creating..."}
                </span>
              ) : editingUserId ? (
                "Save User"
              ) : (
                "Create User"
              )}
            </button>
          </div>
        </fieldset>
      </form>
    </section>
  );
}
