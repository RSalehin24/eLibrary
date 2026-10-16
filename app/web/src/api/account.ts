import { apiRequest } from "./http";
import { apiMutation, emptyMutation } from "./mutation";
import type { AccountProfile, AccountProfileUpdate, TOTPSetup, TOTPStatus } from "./types";

export const readProfile = (signal?: AbortSignal) => apiRequest<AccountProfile>("auth/profile/", { signal });
export const readSecurity = (signal?: AbortSignal) => apiRequest<TOTPStatus>("auth/2fa/status/", { signal });
export const updateProfile = (fields: AccountProfileUpdate) => apiMutation<AccountProfile>("auth/profile/", { method: "PATCH", body: JSON.stringify(fields) });
export const startTOTP = (current_password: string) => apiMutation<TOTPSetup>("auth/2fa/setup/", { method: "POST", body: JSON.stringify({ current_password }) });
export const confirmTOTP = (token: string) => emptyMutation("auth/2fa/confirm/", { method: "POST", body: JSON.stringify({ token }) });
export const cancelTOTP = () => emptyMutation("auth/2fa/cancel/", { method: "POST" });
export const disableTOTP = (fields: { current_password: string; token: string }) => emptyMutation("auth/2fa/disable/", { method: "POST", body: JSON.stringify(fields) });

export function uploadProfileImage(image: File, revision: string) {
  const fields = new FormData(); fields.set("image", image); fields.set("expected_updated_at", revision);
  return apiMutation<AccountProfile>("auth/profile/image/", { method: "POST", body: fields });
}

export const removeProfileImage = (revision: string) => apiMutation<AccountProfile>("auth/profile/image/", { method: "DELETE", body: JSON.stringify({ expected_updated_at: revision }) });
