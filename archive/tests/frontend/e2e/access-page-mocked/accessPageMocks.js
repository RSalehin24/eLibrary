export function createSessionPayload() {
  return {
    authenticated: true,
    user: {
      id: 1,
      email: "superadmin@example.com",
      full_name: "Super Admin",
      profile_image_url: "",
      is_active: true,
      is_staff: true,
      is_superuser: true,
      totp_enabled: false,
      totp_required: false,
      totp_setup_required: false,
      capabilities: [],
    },
  };
}

export function createManagedUsersPayload(requestUrl, users) {
  const url = new URL(requestUrl);
  const offset = Number(url.searchParams.get("offset") || 0);
  const limit = Number(url.searchParams.get("limit") || 60);
  const rows = users.slice(offset, offset + limit);
  const nextOffset = offset + rows.length;

  return {
    rows,
    pagination: {
      offset,
      limit,
      totalCount: users.length,
      hasMore: nextOffset < users.length,
      nextOffset,
    },
  };
}

export function createReferencesPayload(accountScopes, scopedScopes = []) {
  return {
    users: [],
    books: [],
    categories: [],
    writers: [],
    account_scopes: accountScopes,
    scoped_scopes: scopedScopes,
  };
}
