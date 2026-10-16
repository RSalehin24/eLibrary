export function returnPath(path: string) {
  return path.startsWith("/") && !path.startsWith("//") && !/[\\\u0000-\u001f]/.test(path) ? path : "/my-books/";
}
