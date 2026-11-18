export function hasCapability(user, scope) {
  if (!user) {
    return false;
  }

  if (user.is_superuser || user.is_staff) {
    return true;
  }

  const capabilities = user.capabilities || [];
  return capabilities.includes("admin:full_control") || capabilities.includes(scope);
}
