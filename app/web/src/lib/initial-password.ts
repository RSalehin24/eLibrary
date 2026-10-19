export function generateInitialPassword() {
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  return "aA!" + Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}
