import { apiRequest } from "./http";
import { apiMutation } from "./mutation";
import type { AccountMailCollection, AccountMailOperation, Invitation, JobControl, OperationAccepted, PasswordResetAccepted, PasswordResetRequest, ResendInvitation } from "./types";

export const inviteAccount = (values: Invitation) => apiMutation<OperationAccepted>("manage/invitations/", { method: "POST", body: JSON.stringify(values) });
export const resendInvitation = (id: number, values: ResendInvitation) => apiMutation<OperationAccepted>(`manage/users/${id}/invitation/`, { method: "POST", body: JSON.stringify(values) });
export const readAccountMail = (id: number, page: number, signal?: AbortSignal) => apiRequest<AccountMailCollection>(`manage/users/${id}/mail/?page=${page}&limit=10`, { signal });
export const readMailOperation = (id: string, signal?: AbortSignal) => apiRequest<AccountMailOperation>(`manage/mail/${id}/`, { signal });
export const controlMailOperation = (id: string, values: JobControl) => apiMutation<OperationAccepted>(`manage/mail/${id}/`, { method: "POST", body: JSON.stringify(values) });
export const requestPasswordReset = (values: PasswordResetRequest) => apiMutation<PasswordResetAccepted>("auth/password-reset/", { method: "POST", body: JSON.stringify(values) });
