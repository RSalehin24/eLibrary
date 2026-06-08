import { useRef, useState } from "react";
import { authApi } from "../../../api/client";
import { createInitialUserForm } from "../constants";
import { useManagedUserList } from "./useManagedUserList";
import {
  formatApiError,
  generateSuggestedPassword,
  getAccountAccessLabels,
  sortValues,
} from "../utils";
import { isValidEmail, normalizeEmail } from "../../../utils/email";
import { copyPasswordToClipboard } from "./clipboardActions";

export function useAccessUsers({
  allAccountScopeValues,
  applyActiveTab,
  enabled = true,
  loadAdminData,
  scopeLabelMap,
  toast,
}) {
  const [userForm, setUserForm] = useState(() => createInitialUserForm());
  const [editingUserId, setEditingUserId] = useState(null);
  const [pendingDeleteUser, setPendingDeleteUser] = useState(null);
  const [deletingUserId, setDeletingUserId] = useState(null);
  const [resendingSetupUserId, setResendingSetupUserId] = useState(null);
  const [submittingUser, setSubmittingUser] = useState(false);
  const [showCreateUserPassword, setShowCreateUserPassword] = useState(false);
  const userEditorRef = useRef(null);
  const isEditingUser = Boolean(editingUserId);
  const {
    hasMoreManagedUsers,
    loadingMoreUsers,
    loadingUsers,
    observeUsersLoadTrigger,
    refreshUsers,
    refreshingUsers,
    tableShellRef,
    totalManagedUsers,
    updateUsersSearch,
    clearUsersSearch,
    updateUsersSort,
    updateUsersStatus,
    userListFilters,
    usersError,
    visibleManagedUsers,
  } = useManagedUserList({
    enabled,
  });

  function resetUserForm() {
    setEditingUserId(null);
    setUserForm(createInitialUserForm());
    setShowCreateUserPassword(false);
  }

  async function copyPasswordValue(
    password,
    successMessage = "Password copied.",
    showError = true,
  ) {
    await copyPasswordToClipboard({ password, showError, successMessage, toast });
  }

  function toggleUserScope(scopeValue) {
    setUserForm((current) => {
      let nextScopes = current.global_scopes.includes(scopeValue)
        ? current.global_scopes.filter((value) => value !== scopeValue)
        : [...current.global_scopes, scopeValue];
      if (scopeValue === "read:once" && nextScopes.includes("read:once")) {
        nextScopes = nextScopes.filter((value) => value !== "read:durable");
      } else if (scopeValue === "read:durable" && nextScopes.includes("read:durable")) {
        nextScopes = nextScopes.filter((value) => value !== "read:once");
      }
      return {
        ...current,
        global_scopes: sortValues(nextScopes),
      };
    });
  }

  function selectAllAccountPermissions() {
    setUserForm((current) => ({
      ...current,
      global_scopes: sortValues(allAccountScopeValues),
    }));
  }

  function clearAccountPermissions() {
    setUserForm((current) => ({
      ...current,
      global_scopes: [],
    }));
  }

  async function suggestPassword() {
    const password = generateSuggestedPassword();
    setUserForm((current) => ({
      ...current,
      password,
    }));
    await copyPasswordValue(password, "Suggested password copied.");
  }

  function startEditing(entry) {
    setEditingUserId(entry.id);
    setShowCreateUserPassword(false);
    setUserForm({
      email: entry.email,
      full_name: entry.full_name || "",
      password: "",
      is_active: entry.is_active,
      totp_required: entry.totp_required,
      send_invite_email: true,
      global_scopes: sortValues(entry.global_scopes || []),
    });
    applyActiveTab("users");
    window.requestAnimationFrame(() => {
      userEditorRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }

  async function submitUser(event) {
    event.preventDefault();

    if (submittingUser) {
      return;
    }
    if (!event.currentTarget.reportValidity()) {
      return;
    }

    const normalizedEmail = normalizeEmail(userForm.email);

    if (!isEditingUser && !isValidEmail(normalizedEmail)) {
      toast.error("Enter a valid email address.");
      return;
    }

    if (
      !editingUserId &&
      !userForm.send_invite_email &&
      !userForm.password.trim()
    ) {
      toast.error("Enter a password or send an invite email.");
      return;
    }
    if (!userForm.global_scopes.length) {
      toast.error("Select at least one account permission.");
      return;
    }

    const payload = {
      is_active: userForm.is_active,
      totp_required: userForm.totp_required,
      global_scopes: userForm.global_scopes,
    };
    if (!isEditingUser) {
      payload.email = normalizedEmail;
      payload.full_name = userForm.full_name.trim();
      payload.send_invite_email = userForm.send_invite_email;
    }
    if (
      !isEditingUser &&
      !userForm.send_invite_email &&
      userForm.password.trim()
    ) {
      payload.password = userForm.password;
    }

    try {
      setSubmittingUser(true);
      if (editingUserId) {
        await authApi.updateUser(editingUserId, payload);
        toast.success("User updated.");
      } else {
        await authApi.createUser(payload);
        toast.success(
          userForm.send_invite_email
            ? "User created. Setup email sent."
            : "User created.",
        );
      }
      resetUserForm();
      await Promise.all([
        loadAdminData(),
        refreshUsers(),
      ]);
    } catch (error) {
      toast.error(
        formatApiError(error, {
          global_scopes: "Account permissions",
          email: "Email",
          password: "Password",
          is_active: "Active account",
        }),
      );
    } finally {
      setSubmittingUser(false);
    }
  }

  function requestDeleteUser(entry) {
    setPendingDeleteUser(entry);
  }

  async function confirmDeleteUser() {
    if (!pendingDeleteUser || deletingUserId) {
      return;
    }

    try {
      setDeletingUserId(pendingDeleteUser.id);
      await authApi.deleteUser(pendingDeleteUser.id);
      if (editingUserId === pendingDeleteUser.id) {
        resetUserForm();
      }
      setPendingDeleteUser(null);
      toast.success("User deleted.");
      await Promise.all([
        loadAdminData(),
        refreshUsers(),
      ]);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setDeletingUserId(null);
    }
  }

  async function resendSetupEmail(entry) {
    if (!entry?.id || resendingSetupUserId) {
      return;
    }

    try {
      setResendingSetupUserId(entry.id);
      await authApi.resendUserSetupEmail(entry.id);
      toast.success("Setup email sent.");
      await Promise.all([
        loadAdminData(),
        refreshUsers(),
      ]);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setResendingSetupUserId(null);
    }
  }

  return {
    clearAccountPermissions,
    clearUsersSearch,
    confirmDeleteUser,
    copyPasswordValue,
    deletingUserId,
    editingUserId,
    getAccountAccessLabels: (entry) =>
      getAccountAccessLabels(entry, scopeLabelMap),
    hasMoreManagedUsers,
    isEditingUser,
    loadingMoreUsers,
    loadingUsers,
    observeUsersLoadTrigger,
    pendingDeleteUser,
    refreshUsers,
    refreshingUsers,
    requestDeleteUser,
    resendSetupEmail,
    resetUserForm,
    resendingSetupUserId,
    selectAllAccountPermissions,
    setPendingDeleteUser,
    setShowCreateUserPassword,
    setUserForm,
    showCreateUserPassword,
    startEditing,
    submitUser,
    submittingUser,
    suggestPassword,
    tableShellRef,
    totalManagedUsers,
    toggleUserScope,
    updateUsersSearch,
    updateUsersSort,
    updateUsersStatus,
    userEditorRef,
    userForm,
    userListFilters,
    usersError,
    visibleManagedUsers,
  };
}
