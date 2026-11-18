import { authApi } from "../../api/client";
import { emptyTotpSetup } from "./profileModel";

export function useProfileTwoFactorActions({
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
  totpAction
}) {
  async function startSetup() {
    if (totpAction) return;
    try {
      setTotpAction("setup");
      setTotpFeedback("");
      const payload = await authApi.twoFactorSetup();
      setSetup(payload);
      setSetupVisible(true);
      setTwoFactor((current) => ({ ...current, pending_setup: true }));
    } catch (error) {
      setTotpFeedback(error.message || "Could not prepare two-factor setup.");
    } finally {
      setTotpAction("");
    }
  }

  async function openSetup() {
    if (setup.provisioning_uri) {
      setSetupVisible(true);
      return;
    }
    await startSetup();
  }

  async function confirmSetup(event) {
    event.preventDefault();
    if (totpAction) return;
    try {
      setTotpAction("verify");
      setTotpFeedback("");
      await authApi.twoFactorConfirm({ token });
      setToken("");
      setSetup(emptyTotpSetup);
      setSetupVisible(false);
      await refreshSession();
      await loadProfile({ preserveEditor: true });
      toast.success("Two-factor enabled.");
    } catch (error) {
      toast.error(error.message);
    } finally {
      setTotpAction("");
    }
  }

  async function disableTotp() {
    if (totpAction) return;
    try {
      setTotpAction("disable");
      setTotpFeedback("");
      await authApi.twoFactorDisable();
      setToken("");
      setSetup(emptyTotpSetup);
      setSetupVisible(false);
      await refreshSession();
      await loadProfile({ preserveEditor: true });
      toast.success("Two-factor disabled.");
    } catch (error) {
      toast.error(error.message);
    } finally {
      setTotpAction("");
    }
  }

  async function cancelSetup() {
    if (totpAction) return;
    try {
      setTotpAction("cancel");
      setTotpFeedback("");
      await authApi.twoFactorCancel();
      setToken("");
      setSetup(emptyTotpSetup);
      setSetupVisible(false);
      await loadProfile({ preserveEditor: true });
    } catch (error) {
      setTotpFeedback(error.message || "Could not cancel two-factor setup.");
    } finally {
      setTotpAction("");
    }
  }

  async function copyProvisioningUrl() {
    try {
      await navigator.clipboard.writeText(setup.provisioning_uri);
      toast.success("Setup URL copied.");
    } catch {
      toast.error("Could not copy the setup URL.");
    }
  }

  return {
    cancelSetup,
    confirmSetup,
    copyProvisioningUrl,
    disableTotp,
    openSetup
  };
}
