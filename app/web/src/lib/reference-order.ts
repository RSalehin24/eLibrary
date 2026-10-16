export function moveReference<Value>(selection: Value[], index: number, offset: number) {
  const entries = [...selection];
  [entries[index], entries[index + offset]] = [entries[index + offset], entries[index]];
  return entries;
}
