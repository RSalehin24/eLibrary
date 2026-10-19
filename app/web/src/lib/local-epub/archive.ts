const MAX_ARCHIVE_BYTES = 24 * 1024 * 1024;
const MAX_ENTRY_BYTES = 8 * 1024 * 1024;
const MAX_EXPANDED_BYTES = 64 * 1024 * 1024;
const MAX_ENTRIES = 4096;
type Entry = { path: string; method: number; crc: number; size: number; bytes: Uint8Array };

export function archiveEntries(buffer: ArrayBuffer): Entry[] {
  const bytes = new Uint8Array(buffer), view = new DataView(buffer);
  if (bytes.length > MAX_ARCHIVE_BYTES || bytes.length < 22) throw new Error("invalid_archive");
  let end = bytes.length - 22;
  while (end >= Math.max(0, bytes.length - 65557) && view.getUint32(end, true) !== 0x06054b50) end -= 1;
  if (end < 0 || view.getUint32(end, true) !== 0x06054b50) throw new Error("invalid_archive");
  const count = view.getUint16(end + 10, true), start = view.getUint32(end + 16, true);
  if (view.getUint16(end + 4, true) || view.getUint16(end + 6, true) || !count || count > MAX_ENTRIES || view.getUint16(end + 8, true) !== count || end + 22 + view.getUint16(end + 20, true) !== bytes.length) throw new Error("invalid_archive");
  const entries: Entry[] = [], paths = new Set<string>();
  let cursor = start, expanded = 0;
  for (let index = 0; index < count; index += 1) {
    if (cursor + 46 > end || view.getUint32(cursor, true) !== 0x02014b50) throw new Error("invalid_archive");
    const flags = view.getUint16(cursor + 8, true), method = view.getUint16(cursor + 10, true);
    const crc = view.getUint32(cursor + 16, true), compressed = view.getUint32(cursor + 20, true), size = view.getUint32(cursor + 24, true);
    const length = view.getUint16(cursor + 28, true), extra = view.getUint16(cursor + 30, true), comment = view.getUint16(cursor + 32, true), offset = view.getUint32(cursor + 42, true);
    const next = cursor + 46 + length + extra + comment;
    if (next > end || flags & 1 || ![0, 8].includes(method) || size > MAX_ENTRY_BYTES || (expanded += size) > MAX_EXPANDED_BYTES) throw new Error("invalid_archive");
    const path = new TextDecoder("utf-8", { fatal: true }).decode(bytes.subarray(cursor + 46, cursor + 46 + length));
    if (!path || path.startsWith("/") || /[\\\u0000]/.test(path) || path.split("/").some(part => [".", ".."].includes(part)) || paths.has(path)) throw new Error("invalid_archive");
    if (offset + 30 > start || view.getUint32(offset, true) !== 0x04034b50 || view.getUint16(offset + 8, true) !== method || view.getUint16(offset + 6, true) !== flags) throw new Error("invalid_archive");
    const localLength = view.getUint16(offset + 26, true), localExtra = view.getUint16(offset + 28, true), payload = offset + 30 + localLength + localExtra;
    if (payload + compressed > start || localLength !== length || !bytes.subarray(offset + 30, offset + 30 + localLength).every((value, index) => value === bytes[cursor + 46 + index])) throw new Error("invalid_archive");
    paths.add(path); entries.push({ path, method, crc, size, bytes: bytes.slice(payload, payload + compressed) }); cursor = next;
  }
  if (cursor !== end || start + view.getUint32(end + 12, true) !== end) throw new Error("invalid_archive");
  return entries;
}

function checksum(bytes: Uint8Array) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = crc >>> 1 ^ (crc & 1 ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

async function expand(entry: Entry) {
  const stream = new Blob([new Uint8Array(entry.bytes).buffer]).stream();
  const reader = (entry.method === 8 ? stream.pipeThrough(new DecompressionStream("deflate-raw")) : stream).getReader();
  const output = new Uint8Array(entry.size);
  let cursor = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (cursor + value.length > output.length) throw new Error("invalid_archive");
      output.set(value, cursor); cursor += value.length;
    }
  } catch (error) { await reader.cancel(); throw error; }
  if (cursor !== output.length || checksum(output) !== entry.crc) throw new Error("invalid_archive");
  return output;
}

export async function readLocalArchive(file: File) {
  const entries = archiveEntries(await file.arrayBuffer()), files = new Map<string, Uint8Array>();
  for (const entry of entries) if (!entry.path.endsWith("/")) files.set(entry.path, await expand(entry));
  if (new TextDecoder().decode(files.get("mimetype")) !== "application/epub+zip") throw new Error("invalid_epub");
  return files;
}
