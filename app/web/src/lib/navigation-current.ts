const relatedRoutes: Readonly<Record<string, readonly string[]>> = {
  "/catalog/": ["/books/", "/contributors/", "/categories/", "/series/", "/collections/"],
  "/my-books/": [],
  "/manage/sources/": ["/manage/unfinished/"],
  "/manage/books/": ["/manage/book-creations/"],
};

export function navigationIsCurrent(pathname: string, href: string) {
  if (pathname === href) return true;
  if (href === "/manage/") return false;
  return [href, ...(relatedRoutes[href] ?? [])].some(prefix => pathname.startsWith(prefix));
}
