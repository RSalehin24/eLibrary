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
export async function mockAuthenticatedSession(page, userOverrides = {}) {
  await page.route(/\/api\/auth\/session\/?(?:\?.*)?$/, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(createSessionPayload(userOverrides))
    });
  });
  await page.route(/\/api\/csrf\/?(?:\?.*)?$/, async route => {
    await route.fulfill({
      status: 204,
      body: ""
    });
  });
}
export async function mockCatalogBooksApi(page, total = 24, options = {}) {
  const books = Array.from({
    length: total
  }, (_, index) => createBook(index));
  const {
    savedFilters = []
  } = options;
  await page.route("**/api/catalog/books/**", async route => {
    const url = new URL(route.request().url());
    const currentPage = Number(url.searchParams.get("page") || "1");
    const limit = Number(url.searchParams.get("limit") || "60");
    const startIndex = (currentPage - 1) * limit;
    const entries = books.slice(startIndex, startIndex + limit);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        entries,
        pagination: {
          page: currentPage,
          limit,
          total_count: books.length,
          page_count: Math.max(1, Math.ceil(books.length / limit)),
          has_previous: currentPage > 1,
          has_next: startIndex + entries.length < books.length
        }
      })
    });
  });
  await page.route("**/api/saved-filters/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(savedFilters)
    });
  });
  const filterSuggestions = [
    { name: "Architecture" },
    { name: "History" },
  ];
  await page.route("**/api/catalog/writers/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(filterSuggestions)
    });
  });
  await page.route("**/api/catalog/series/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(filterSuggestions)
    });
  });
  await page.route("**/api/catalog/categories/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(filterSuggestions)
    });
  });
}
export async function mockAccessApi(page, totalUsers = 2) {
  const users = [{
    id: 1,
    email: "responsive-admin@example.com",
    full_name: "Responsive Admin",
    is_active: true,
    is_superuser: true,
    totp_required: false,
    totp_enabled: true,
    global_scopes: ["admin:access"],
    grant_count: 0,
    can_resend_setup_email: false
  }, ...Array.from({
    length: Math.max(totalUsers - 1, 1)
  }, (_, index) => ({
    id: 77 + index,
    email: `pending-user-${index + 1}@example.com`,
    full_name: `Pending User ${index + 1}`,
    is_active: index % 4 !== 0,
    is_superuser: false,
    totp_required: index % 2 === 0,
    totp_enabled: index % 2 !== 0,
    global_scopes: index % 3 === 0 ? ["read:durable", "metadata:edit"] : ["read:durable"],
    grant_count: index % 3 + 1,
    can_resend_setup_email: index % 2 === 0
  }))].slice(0, totalUsers);
  function managedUsersPayload(requestUrl) {
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
        nextOffset
      }
    };
  }
  await page.route("**/api/auth/users/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(managedUsersPayload(route.request().url()))
    });
  });
  await page.route("**/api/access/grants/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([])
    });
  });
  await page.route("**/api/access/references/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        users: [],
        books: [],
        categories: [],
        writers: [],
        account_scopes: [{
          value: "read:durable",
          label: "Read durable books"
        }, {
          value: "metadata:edit",
          label: "Edit metadata"
        }],
        scoped_scopes: [{
          value: "read:durable",
          label: "Read durable books"
        }, {
          value: "metadata:edit",
          label: "Edit metadata"
        }]
      })
    });
  });
}
export async function mockProfileApi(page) {
  const profile = {
    id: 1,
    email: "profile-user@example.com",
    full_name: "Profile User",
    profile_image_url: "",
    kindle_emails: ["reader@kindle.com"],
    kindle_sender_email: "library-sender@example.com",
    is_active: true,
    is_staff: false,
    is_superuser: false
  };
  await page.route("**/api/auth/profile/", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(profile)
    });
  });
  await page.route("**/api/auth/2fa/status/", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        enabled: false,
        pending_setup: false,
        required: false,
        setup_required: false
      })
    });
  });
}
export async function mockManualBooksApi(page, total = 8) {
  const books = Array.from({
    length: total
  }, (_, index) => createBook(index, {
    id: `manual-${index + 1}`,
    slug: `manual-book-${index + 1}`,
    catalog_code: `MB-${String(index + 1).padStart(3, "0")}`,
    title: `Manual Book ${index + 1}`,
    record_type: "manual"
  }));
  await page.route("**/api/catalog/manual-books/**", async route => {
    const url = new URL(route.request().url());
    const currentPage = Number(url.searchParams.get("page") || "1");
    const limit = Number(url.searchParams.get("limit") || "60");
    const startIndex = (currentPage - 1) * limit;
    const entries = books.slice(startIndex, startIndex + limit);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        entries,
        pagination: {
          page: currentPage,
          limit,
          total_count: books.length,
          page_count: Math.max(1, Math.ceil(books.length / limit)),
          has_previous: currentPage > 1,
          has_next: startIndex + entries.length < books.length
        }
      })
    });
  });
  const suggestionPayloads = {
    categories: [{
      name: "Architecture"
    }, {
      name: "History"
    }],
    writers: [{
      name: "Ada Writer"
    }, {
      name: "Bea Writer"
    }],
    translators: [{
      name: "Sam Translator"
    }],
    compilers: [{
      name: "Casey Compiler"
    }],
    editors: [{
      name: "Evan Editor"
    }]
  };
  await page.route("**/api/catalog/categories/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(suggestionPayloads.categories)
    });
  });
  await page.route("**/api/catalog/writers/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(suggestionPayloads.writers)
    });
  });
  await page.route("**/api/catalog/series/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(suggestionPayloads.categories)
    });
  });
  await page.route("**/api/catalog/translators/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(suggestionPayloads.translators)
    });
  });
  await page.route("**/api/catalog/compilers/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(suggestionPayloads.compilers)
    });
  });
  await page.route("**/api/catalog/editors/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(suggestionPayloads.editors)
    });
  });
}
