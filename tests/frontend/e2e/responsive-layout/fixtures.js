export function createSessionPayload(overrides = {}) {
  return {
    authenticated: true,
    user: {
      id: 1,
      email: "responsive-admin@example.com",
      full_name: "Responsive Admin",
      profile_image_url: "",
      is_active: true,
      is_staff: true,
      is_superuser: true,
      capabilities: ["processing:manage"],
      totp_enabled: false,
      totp_required: false,
      totp_setup_required: false,
      ...overrides
    }
  };
}
export function createBook(index, overrides = {}) {
  const bookNumber = String(index + 1).padStart(3, "0");
  return {
    id: `book-${bookNumber}`,
    slug: `responsive-book-${bookNumber}`,
    catalog_code: `BK-${bookNumber}`,
    title: `Responsive Book ${bookNumber}`,
    authors: [`Writer ${bookNumber}`],
    categories: [`Category ${index % 4}`],
    series: index % 2 === 0 ? [`Series ${index % 3}`] : [],
    record_type: index % 5 === 0 ? "manual" : "digital",
    created_at: `2026-04-${String(index % 28 + 1).padStart(2, "0")}T08:00:00Z`,
    latest_submission_at: `2026-04-${String(index % 28 + 1).padStart(2, "0")}T09:00:00Z`,
    primary_source: {
      display_path: `source/${bookNumber}`
    },
    ...overrides
  };
}
