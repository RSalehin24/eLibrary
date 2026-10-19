function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) { crc ^= byte; for (let bit = 0; bit < 8; bit += 1) crc = crc >>> 1 ^ (crc & 1 ? 0xedb88320 : 0); }
  return (crc ^ 0xffffffff) >>> 0;
}

function zip(entries) {
  const bodies = [], directory = [];
  let offset = 0;
  for (const [path, text] of entries) {
    const name = Buffer.from(path), bytes = Buffer.from(text), crc = crc32(bytes), local = Buffer.alloc(30), central = Buffer.alloc(46);
    local.writeUInt32LE(0x04034b50); local.writeUInt16LE(20, 4); local.writeUInt32LE(crc, 14); local.writeUInt32LE(bytes.length, 18); local.writeUInt32LE(bytes.length, 22); local.writeUInt16LE(name.length, 26);
    central.writeUInt32LE(0x02014b50); central.writeUInt16LE(20, 4); central.writeUInt16LE(20, 6); central.writeUInt32LE(crc, 16); central.writeUInt32LE(bytes.length, 20); central.writeUInt32LE(bytes.length, 24); central.writeUInt16LE(name.length, 28); central.writeUInt32LE(offset, 42);
    bodies.push(local, name, bytes); directory.push(central, name); offset += local.length + name.length + bytes.length;
  }
  const contents = Buffer.concat(directory), end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50); end.writeUInt16LE(entries.length, 8); end.writeUInt16LE(entries.length, 10); end.writeUInt32LE(contents.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...bodies, contents, end]);
}

export function localEPUB() {
  const paragraphs = Array.from({ length: 40 }, (_, index) => `<p id="line-${index}">অনুচ্ছেদ ${index + 1}: বাংলা বই পড়ার জন্য লেখা। একটি সুন্দর গল্প চলতে থাকে।</p>`).join("");
  return zip([
    ["mimetype", "application/epub+zip"],
    ["META-INF/container.xml", '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'],
    ["OEBPS/content.opf", '<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>নিজের বাংলা বই</dc:title></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/><item id="two" href="two.xhtml" media-type="application/xhtml+xml"/><item id="toc" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="one"/><itemref idref="two"/></spine></package>'],
    ["OEBPS/nav.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li><a href="one.xhtml">প্রথম অধ্যায়</a><ol><li><a href="one.xhtml#line-10">প্রথম অংশ</a></li></ol></li><li><a href="two.xhtml">দ্বিতীয় অধ্যায়</a></li></ol></nav></body></html>'],
    ["OEBPS/one.xhtml", `<html xmlns="http://www.w3.org/1999/xhtml"><head><title>প্রথম অধ্যায়</title></head><body><h1>প্রথম অধ্যায়</h1>${paragraphs}<a href="two.xhtml#second">পরের অধ্যায়ের লিংক</a><script>parent.localFileScriptRan=true</script><img src="https://should-not-load.invalid/pixel" onerror="parent.localFileScriptRan=true"/><iframe src="https://should-not-load.invalid/"></iframe></body></html>`],
    ["OEBPS/two.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>দ্বিতীয় অধ্যায়</title></head><body><h1 id="second">দ্বিতীয় অধ্যায়</h1><p>শেষ অধ্যায়ের সম্পূর্ণ বাংলা লেখা।</p></body></html>'],
  ]);
}
