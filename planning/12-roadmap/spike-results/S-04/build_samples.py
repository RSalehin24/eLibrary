# Throwaway spike code (S-04): hand-assemble EPUB 3 samples with the standard library only.
import struct, sys, zlib, zipfile, pathlib

out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
font = pathlib.Path("/usr/share/fonts/noto/NotoSansBengali-Light.ttf").read_bytes()

def png() -> bytes:
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    raw = b"".join(b"\x00" + bytes([200, 120, 40]) * 8 for _ in range(8))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")

CONTAINER = '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
OPF = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id" xml:lang="bn">
 <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:identifier id="id">urn:uuid:67e55044-10b1-426f-9247-bb680e5fe0c8</dc:identifier>
  <dc:title>নমুনা বই</dc:title><dc:language>bn</dc:language><dc:creator>নমুনা লেখক</dc:creator>
  <meta property="dcterms:modified">2026-11-20T00:00:00Z</meta>
 </metadata>
 <manifest>
  <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
  <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  <item id="c1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  <item id="css" href="style.css" media-type="text/css"/>
  <item id="img" href="cover.png" media-type="image/png" properties="cover-image"/>
  <item id="font" href="font.ttf" media-type="font/ttf"/>
 </manifest>
 <spine toc="ncx"><itemref idref="c1"/></spine>
</package>'''
NAV = '<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="bn" lang="bn"><head><title>সূচি</title></head><body><nav epub:type="toc"><ol><li><a href="chapter1.xhtml">প্রথম অধ্যায়</a></li></ol></nav></body></html>'
NCX = '<?xml version="1.0" encoding="UTF-8"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head><meta name="dtb:uid" content="urn:uuid:67e55044-10b1-426f-9247-bb680e5fe0c8"/></head><docTitle><text>নমুনা বই</text></docTitle><navMap><navPoint id="n1" playOrder="1"><navLabel><text>প্রথম অধ্যায়</text></navLabel><content src="chapter1.xhtml"/></navPoint></navMap></ncx>'
CHAPTER = '<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" xml:lang="bn" lang="bn"><head><title>প্রথম অধ্যায়</title><link rel="stylesheet" type="text/css" href="style.css"/></head><body><h1>প্রথম অধ্যায়</h1><p>বাংলা ভাষা আমাদের গর্ব। এটি একটি নমুনা অনুচ্ছেদ।</p><img src="cover.png" alt="নমুনা ছবি"/></body></html>'
CSS = '@font-face { font-family: "Sample"; src: url(font.ttf); } body { font-family: "Sample", serif; }'

def build(name, mutate=None):
    files = {"META-INF/container.xml": CONTAINER, "OEBPS/content.opf": OPF, "OEBPS/nav.xhtml": NAV,
             "OEBPS/toc.ncx": NCX, "OEBPS/chapter1.xhtml": CHAPTER, "OEBPS/style.css": CSS,
             "OEBPS/cover.png": png(), "OEBPS/font.ttf": font}
    compress_mimetype = False
    if mutate:
        files, compress_mimetype = mutate(files)
    with zipfile.ZipFile(out / name, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                   compress_type=zipfile.ZIP_DEFLATED if compress_mimetype else zipfile.ZIP_STORED)
        for path, data in files.items():
            z.writestr(path, data, compress_type=zipfile.ZIP_DEFLATED)

build("valid.epub")
build("broken-missing-nav.epub", lambda f: ({k: v for k, v in f.items() if k != "OEBPS/nav.xhtml"}, False))
build("broken-missing-file.epub", lambda f: ({k: v for k, v in f.items() if k != "OEBPS/cover.png"}, False))
build("broken-malformed-xhtml.epub", lambda f: ({**f, "OEBPS/chapter1.xhtml": f["OEBPS/chapter1.xhtml"].replace("</p>", "")}, False))
build("broken-mimetype-compressed.epub", lambda f: (f, True))
build("broken-no-language.epub", lambda f: ({**f, "OEBPS/content.opf": f["OEBPS/content.opf"].replace("<dc:language>bn</dc:language>", "")}, False))
