export type WorkspaceNavigationEntry = Readonly<{ href: string; label: string }>;

const entries = [
  { section: "sources", href: "/manage/sources/", label: "বই তৈরি" },
  { section: "books", href: "/manage/books/", label: "সব বই" },
  { section: "books", href: "/manage/entities/", label: "লেখক ও বিভাগ" },
  { section: "jobs", href: "/manage/jobs/", label: "কাজের অবস্থা" },
  { section: "automations", href: "/manage/automations/", label: "সময়সূচি" },
  { section: "users-access", href: "/manage/users-access/", label: "ব্যবহারকারী" },
];

export function managementNavigation(sections: readonly string[]): WorkspaceNavigationEntry[] {
  return entries.filter(entry => sections.includes(entry.section));
}

export function managementHome(sections: readonly string[]) {
  return managementNavigation(sections)[0]?.href ?? "/manage/overview/";
}
