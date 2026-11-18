export async function copyPasswordToClipboard({
  password,
  showError = true,
  successMessage = "Password copied.",
  toast
}) {
  if (!password) {
    if (showError) {
      toast.error("Generate or enter a password first.");
    }
    return;
  }

  try {
    await navigator.clipboard.writeText(password);
    toast.success(successMessage);
  } catch {
    if (showError) {
      toast.error("Could not copy the password.");
    }
  }
}
