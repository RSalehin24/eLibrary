export function returnPath(path: string, fallback = "/my-books/") {
  return path.startsWith("/") && !path.startsWith("//") && !/[\\\u0000-\u001f]/.test(path) ? path : fallback;
}
