export function documentLink(event: MouseEvent): HTMLAnchorElement | null {
  const target = event.target;
  if (!target || !(target as Element).closest) return null;
  return (target as Element).closest("a[href]") as HTMLAnchorElement | null;
}

export function chapterFromURL(target: URL, resourceBase: string, chapters: { path: string }[]): number {
  const base = new URL(resourceBase, window.location.origin);
  if (target.origin !== base.origin || !target.pathname.startsWith(base.pathname)) return -1;
  let path: string;
  try { path = decodeURIComponent(target.pathname.slice(base.pathname.length)); }
  catch { return -1; }
  return chapters.findIndex((chapter) => chapter.path === path);
}
