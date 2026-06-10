export const bookPropertiesItems = [
  { to: "/library", label: "Books" },
  { to: "/categories", label: "Categories" },
  { to: "/series", label: "Series" },
  { to: "/writers", label: "Writers" },
  { to: "/manual-books", label: "Physical Books' List" },
];

export const processingItems = [
  {
    to: "/catalog",
    label: "Catalog",
    capabilityRequired: true,
  },
  {
    to: "/create",
    label: "Create",
    capabilityRequired: true,
  },
  {
    to: "/on-hold",
    label: "On Hold",
    capabilityRequired: true,
  },
  {
    to: "/incomplete",
    label: "Incomplete",
    capabilityRequired: true,
  },
  {
    to: "/multipage-toc",
    label: "Multi-page TOC",
    capabilityRequired: true,
  },
  {
    to: "/reprocessing",
    label: "Reprocessing",
    capabilityRequired: true,
  },
];

export function isBookPropertiesRoute(pathname) {
  return (
    pathname === "/library" ||
    pathname === "/categories" ||
    pathname === "/series" ||
    pathname === "/writers" ||
    pathname === "/translators" ||
    pathname === "/editors" ||
    pathname === "/publishers" ||
    pathname === "/manual-books" ||
    pathname.startsWith("/books/")
  );
}

export function isProcessingRoute(pathname) {
  return (
    pathname === "/catalog" ||
    pathname === "/create" ||
    pathname === "/on-hold" ||
    pathname === "/incomplete" ||
    pathname === "/multipage-toc" ||
    pathname === "/reprocessing" ||
    pathname.startsWith("/processing")
  );
}

export function getHomePath(user) {
  return user?.is_superuser ? "/home" : "/my-books";
}

export function authenticatedNavigation(user) {
  if (!user) {
    return [];
  }

  if (user.is_superuser) {
    return [
      { to: "/home", label: "Home" },
      { to: "/access", label: "Users & Access" },
    ];
  }

  return [
    { to: "/my-books", label: "My Books" },
    { to: "/kindle-sent", label: "Kindle" },
    { to: "/home", label: "All Books" },
    { to: "/access", label: "Users & Access" },
    { to: "/notes", label: "My Notes" },
  ];
}

export function primaryNavigation(user) {
  if (!user) {
    return [];
  }

  if (user.is_superuser) {
    return [
      { to: "/home", label: "Home" },
      { to: "/access", label: "Users & Access" },
    ];
  }

  const items = [{ to: "/my-books", label: "My Books" }];

  if (
    user.is_superuser ||
    (user.capabilities || []).includes("admin:full_control") ||
    (user.capabilities || []).includes("send:kindle")
  ) {
    items.push({ to: "/kindle-sent", label: "Kindle" });
  }

  return items;
}

export function secondaryNavigation(user) {
  if (!user) {
    return [];
  }

  if (user.is_superuser) {
    return [];
  }

  const items = [];

  if (
    user.is_superuser ||
    (user.capabilities || []).includes("admin:full_control") ||
    (user.capabilities || []).includes("access:manage")
  ) {
    items.push({ to: "/access", label: "Users & Access" });
  }

  return items;
}

export function hasNotesLink(user) {
  if (!user) {
    return false;
  }
  return !user.is_superuser;
}
