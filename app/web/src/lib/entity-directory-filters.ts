export const directorySortLabels: Readonly<Record<string, string>> = {
  "": "সেরা মিল", name: "নাম: অ থেকে হ", "-name": "নাম: হ থেকে অ",
  "-book_count": "বেশি বই আগে", book_count: "কম বই আগে",
  catalog_code: "কোড: ছোট থেকে বড়", "-catalog_code": "কোড: বড় থেকে ছোট",
  "-created_at": "নতুন যোগ হওয়া আগে", created_at: "আগে যোগ হওয়া আগে",
};

export function validDirectoryDate(value: string) {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value) || Number(value.slice(0, 4)) < 1) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

export function validDirectoryFilters(values: Record<string, string>) {
  if (values.sort && !Object.hasOwn(directorySortLabels, values.sort)) return false;
  if ([values.created_after, values.created_before].some(value => value && !validDirectoryDate(value))) return false;
  return !values.created_after || !values.created_before || values.created_after <= values.created_before;
}
