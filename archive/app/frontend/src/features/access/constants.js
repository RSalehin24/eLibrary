export const initialReferences = {
  books: [],
  categories: [],
  writers: [],
  account_scopes: [],
  scoped_scopes: [],
};

export const initialGrantForm = {
  user: "",
  scopes: [],
  targetType: "book",
  targetIds: [],
};

export function createInitialUserForm() {
  return {
    email: "",
    full_name: "",
    password: "",
    is_active: true,
    totp_required: false,
    send_invite_email: true,
    global_scopes: [],
  };
}

export function normalizeAccessTab(tab) {
  return tab === "access" ? "access" : "users";
}
