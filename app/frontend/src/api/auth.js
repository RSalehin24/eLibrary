import { apiFetch } from "./http";
import { toQueryString } from "../utils/query";

export const authApi = {
  session: () => apiFetch("/auth/session/"),
  demoLogin: () => apiFetch("/auth/demo-login/"),
  login: (body) => apiFetch("/auth/login/", { method: "POST", body }),
  logout: () => apiFetch("/auth/logout/", { method: "POST" }),
  profile: () => apiFetch("/auth/profile/"),
  updateProfile: (body) =>
    apiFetch("/auth/profile/", { method: "PATCH", body }),
  users: (params) => apiFetch(`/auth/users/${toQueryString(params)}`),
  createUser: (body) => apiFetch("/auth/users/", { method: "POST", body }),
  updateUser: (id, body) =>
    apiFetch(`/auth/users/${id}/`, { method: "PATCH", body }),
  deleteUser: (id) => apiFetch(`/auth/users/${id}/`, { method: "DELETE" }),
  resendUserSetupEmail: (id) =>
    apiFetch(`/auth/users/${id}/resend-setup-email/`, {
      method: "POST",
      body: {},
    }),
  passwordReset: (body) =>
    apiFetch("/auth/password-reset/", { method: "POST", body }),
  passwordResetValidate: (body) =>
    apiFetch("/auth/password-reset/validate/", { method: "POST", body }),
  passwordResetConfirm: (body) =>
    apiFetch("/auth/password-reset/confirm/", { method: "POST", body }),
  twoFactorStatus: () => apiFetch("/auth/2fa/status/"),
  twoFactorSetup: () => apiFetch("/auth/2fa/setup/", { method: "POST" }),
  twoFactorConfirm: (body) =>
    apiFetch("/auth/2fa/confirm/", { method: "POST", body }),
  twoFactorCancel: () =>
    apiFetch("/auth/2fa/cancel/", { method: "POST", body: {} }),
  twoFactorDisable: () =>
    apiFetch("/auth/2fa/disable/", { method: "POST", body: {} }),
};
