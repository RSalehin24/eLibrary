// ── ZIP writer (no external dependency) ──────────────────────────────────────

/** CRC-32 lookup table */
const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[i] = c;
  }
  return table;
})();

function crc32(data) {
  let crc = 0xffffffff;
  for (let i = 0; i < data.length; i++) {
    crc = CRC_TABLE[(crc ^ data[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function uint16LE(n) {
  return [(n & 0xff), (n >> 8) & 0xff];
}
function uint32LE(n) {
  const u = n >>> 0;
  return [(u & 0xff), (u >> 8) & 0xff, (u >> 16) & 0xff, (u >> 24) & 0xff];
}

const encoder = new TextEncoder();

export function buildZip(files) {
  // files: Array<{ name: string, data: string }>
  const localHeaders = [];
  const centralDirs = [];
  let offset = 0;

  for (const { name, data } of files) {
    const nameBytes = encoder.encode(name);
    const dataBytes = encoder.encode(data);
    const crc = crc32(dataBytes);
    const size = dataBytes.length;

    // Local file header
    const local = new Uint8Array([
      0x50, 0x4b, 0x03, 0x04, // signature
      0x14, 0x00,             // version needed: 2.0
      0x00, 0x00,             // flags
      0x00, 0x00,             // compression: store
      0x00, 0x00,             // mod time
      0x00, 0x00,             // mod date
      ...uint32LE(crc),
      ...uint32LE(size),
      ...uint32LE(size),
      ...uint16LE(nameBytes.length),
      0x00, 0x00,             // extra field length
      ...nameBytes,
      ...dataBytes,
    ]);

    localHeaders.push(local);

    // Central directory entry
    const central = new Uint8Array([
      0x50, 0x4b, 0x01, 0x02, // signature
      0x14, 0x00,             // version made by
      0x14, 0x00,             // version needed
      0x00, 0x00,             // flags
      0x00, 0x00,             // compression: store
      0x00, 0x00,             // mod time
      0x00, 0x00,             // mod date
      ...uint32LE(crc),
      ...uint32LE(size),
      ...uint32LE(size),
      ...uint16LE(nameBytes.length),
      0x00, 0x00,             // extra field length
      0x00, 0x00,             // comment length
      0x00, 0x00,             // disk start
      0x00, 0x00,             // internal attr
      0x00, 0x00, 0x00, 0x00, // external attr
      ...uint32LE(offset),
      ...nameBytes,
    ]);

    centralDirs.push(central);
    offset += local.length;
  }

  const centralSize = centralDirs.reduce((s, b) => s + b.length, 0);

  // End of central directory record
  const eocd = new Uint8Array([
    0x50, 0x4b, 0x05, 0x06,
    0x00, 0x00,
    0x00, 0x00,
    ...uint16LE(files.length),
    ...uint16LE(files.length),
    ...uint32LE(centralSize),
    ...uint32LE(offset),
    0x00, 0x00,
  ]);

  const totalSize =
    localHeaders.reduce((s, b) => s + b.length, 0) + centralSize + eocd.length;
  const out = new Uint8Array(totalSize);
  let pos = 0;
  for (const b of localHeaders) { out.set(b, pos); pos += b.length; }
  for (const b of centralDirs) { out.set(b, pos); pos += b.length; }
  out.set(eocd, pos);
  return out;
}

