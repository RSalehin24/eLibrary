import { MAX_CELL_LINES, PDF_COLUMNS, PDF_LAYOUT } from "./constants";
import { clampLines, concatUint8Arrays, downloadBlob, slugifyFilename, wrapText } from "./helpers";
import { bookExportRows } from "./rows";

function createPdfCanvas() {
  const canvas = document.createElement("canvas");
  canvas.width = PDF_LAYOUT.canvasWidth * PDF_LAYOUT.scale;
  canvas.height = PDF_LAYOUT.canvasHeight * PDF_LAYOUT.scale;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Unable to create PDF canvas.");
  }
  context.scale(PDF_LAYOUT.scale, PDF_LAYOUT.scale);
  context.textBaseline = "top";
  return { canvas, context };
}

function drawPageChrome(context, title, rowCount, pageNumber) {
  context.fillStyle = "#f4f8f6";
  context.fillRect(0, 0, PDF_LAYOUT.canvasWidth, PDF_LAYOUT.canvasHeight);
  context.fillStyle = "#ffffff";
  context.fillRect(18, 18, PDF_LAYOUT.canvasWidth - 36, PDF_LAYOUT.canvasHeight - 36);
  context.fillStyle = "rgba(238, 211, 121, 0.18)";
  context.beginPath();
  context.arc(PDF_LAYOUT.canvasWidth - 92, 74, 72, 0, Math.PI * 2);
  context.fill();
  context.fillStyle = "rgba(15, 75, 56, 0.08)";
  context.fillRect(PDF_LAYOUT.marginX, 22, PDF_LAYOUT.canvasWidth - PDF_LAYOUT.marginX * 2, 4);
  context.fillStyle = "#17392f";
  context.font = '700 26px "Avenir Next", "Noto Sans Bengali", "Hind Siliguri", sans-serif';
  context.fillText(title, PDF_LAYOUT.marginX, PDF_LAYOUT.titleY);
  context.fillStyle = "#5d7068";
  context.font = '500 12px "Avenir Next", "Noto Sans Bengali", "Hind Siliguri", sans-serif';
  context.fillText(`${rowCount} books exported`, PDF_LAYOUT.marginX, PDF_LAYOUT.subtitleY);
  const dateLabel = new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" }).format(new Date());
  const metaLabel = `${dateLabel}  •  Page ${pageNumber}`;
  const metaWidth = context.measureText(metaLabel).width;
  context.fillText(metaLabel, PDF_LAYOUT.canvasWidth - PDF_LAYOUT.marginX - metaWidth, PDF_LAYOUT.subtitleY);
}

function drawTableHeader(context, startY) {
  let x = PDF_LAYOUT.marginX;
  context.fillStyle = "#17392f";
  context.fillRect(PDF_LAYOUT.marginX, startY, PDF_LAYOUT.canvasWidth - PDF_LAYOUT.marginX * 2, PDF_LAYOUT.headerHeight);
  PDF_COLUMNS.forEach((column) => {
    context.fillStyle = "#edf6f1";
    context.font = '700 11px "Avenir Next", "Noto Sans Bengali", "Hind Siliguri", sans-serif';
    context.fillText(column.label, x + PDF_LAYOUT.cellPaddingX, startY + 11);
    context.strokeStyle = "rgba(255, 255, 255, 0.16)";
    context.strokeRect(x, startY, column.width, PDF_LAYOUT.headerHeight);
    x += column.width;
  });
  return startY + PDF_LAYOUT.headerHeight;
}

function preparePdfCellMap(row) {
  return {
    catalogCode: row.catalogCode || "Pending",
    title: row.title || "Untitled",
    contributors: row.contributors || "Contributor unavailable",
    categories: row.categories || "Unsorted",
    series: row.series || "Standalone",
    price: row.price || "",
    type: row.type || "",
    createdAt: row.createdAt || "",
  };
}

function preparePdfRow(context, row) {
  const cellMap = preparePdfCellMap(row);
  const lineMap = {};
  let maxLines = 1;
  PDF_COLUMNS.forEach((column) => {
    context.font = `${column.weight || 500} 12px "Avenir Next", "Noto Sans Bengali", "Hind Siliguri", sans-serif`;
    const maxTextWidth = column.width - PDF_LAYOUT.cellPaddingX * 2;
    const lines = clampLines(context, wrapText(context, cellMap[column.key], maxTextWidth), MAX_CELL_LINES, maxTextWidth);
    lineMap[column.key] = lines;
    maxLines = Math.max(maxLines, lines.length);
  });
  return {
    lineMap,
    rowHeight: Math.max(PDF_LAYOUT.rowMinHeight, PDF_LAYOUT.cellPaddingY * 2 + maxLines * PDF_LAYOUT.lineHeight),
  };
}

function drawPdfRow(context, preparedRow, startY, rowIndex) {
  let x = PDF_LAYOUT.marginX;
  const tableWidth = PDF_LAYOUT.canvasWidth - PDF_LAYOUT.marginX * 2;
  context.fillStyle = rowIndex % 2 === 0 ? "#ffffff" : "#f7faf8";
  context.fillRect(PDF_LAYOUT.marginX, startY, tableWidth, preparedRow.rowHeight);
  PDF_COLUMNS.forEach((column) => {
    const lines = preparedRow.lineMap[column.key];
    context.strokeStyle = "#d8e4de";
    context.strokeRect(x, startY, column.width, preparedRow.rowHeight);
    lines.forEach((line, lineIndex) => {
      context.fillStyle = column.key === "catalogCode" ? "#0f4b38" : "#17392f";
      context.font = `${column.weight || 500} 12px "Avenir Next", "Noto Sans Bengali", "Hind Siliguri", sans-serif`;
      context.fillText(line, x + PDF_LAYOUT.cellPaddingX, startY + PDF_LAYOUT.cellPaddingY + lineIndex * PDF_LAYOUT.lineHeight);
    });
    x += column.width;
  });
}

function renderPdfPages(rows, title) {
  const pages = [];
  let pageNumber = 1;
  let current = createPdfCanvas();
  let currentY = drawTableHeader((drawPageChrome(current.context, title, rows.length, pageNumber), current.context), PDF_LAYOUT.tableY);
  rows.forEach((row, rowIndex) => {
    const preparedRow = preparePdfRow(current.context, row);
    const maxY = PDF_LAYOUT.canvasHeight - PDF_LAYOUT.marginY - 18;
    if (currentY + preparedRow.rowHeight > maxY) {
      pages.push(current.canvas);
      pageNumber += 1;
      current = createPdfCanvas();
      drawPageChrome(current.context, title, rows.length, pageNumber);
      currentY = drawTableHeader(current.context, PDF_LAYOUT.tableY);
    }
    drawPdfRow(current.context, preparedRow, currentY, rowIndex);
    currentY += preparedRow.rowHeight;
  });
  pages.push(current.canvas);
  return pages;
}

async function canvasToJpegBytes(canvas) {
  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob(
      (result) => (result ? resolve(result) : reject(new Error("Unable to render PDF page."))),
      "image/jpeg",
      0.92,
    );
  });
  return new Uint8Array(await blob.arrayBuffer());
}

function buildPdfBlob(pages) {
  const encoder = new TextEncoder();
  const chunks = [];
  const objectOffsets = [];
  let position = 0;
  const push = (value) => {
    const bytes = typeof value === "string" ? encoder.encode(value) : value;
    chunks.push(bytes);
    position += bytes.length;
  };
  const beginObject = (id) => {
    objectOffsets[id] = position;
    push(`${id} 0 obj\n`);
  };

  push(new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34, 0x0a, 0x25, 0xff, 0xff, 0xff, 0xff, 0x0a]));
  const objectCount = 2 + pages.length * 3;
  const pageRefs = pages.map((_, index) => 3 + index * 3);

  beginObject(1);
  push("<< /Type /Catalog /Pages 2 0 R >>\nendobj\n");
  beginObject(2);
  push(`<< /Type /Pages /Count ${pages.length} /Kids [${pageRefs.map((ref) => `${ref} 0 R`).join(" ")}] >>\nendobj\n`);

  pages.forEach((page, index) => {
    const pageObjectId = 3 + index * 3;
    const imageObjectId = pageObjectId + 1;
    const contentObjectId = pageObjectId + 2;
    const imageName = `Im${index + 1}`;
    beginObject(pageObjectId);
    push(`<< /Type /Page /Parent 2 0 R /Resources << /XObject << /${imageName} ${imageObjectId} 0 R >> >> /MediaBox [0 0 ${PDF_LAYOUT.pdfWidth} ${PDF_LAYOUT.pdfHeight}] /Contents ${contentObjectId} 0 R >>\nendobj\n`);
    beginObject(imageObjectId);
    push(`<< /Type /XObject /Subtype /Image /Width ${page.width} /Height ${page.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${page.bytes.length} >>\nstream\n`);
    push(page.bytes);
    push("\nendstream\nendobj\n");
    const contentBytes = encoder.encode(`q\n${PDF_LAYOUT.pdfWidth} 0 0 ${PDF_LAYOUT.pdfHeight} 0 0 cm\n/${imageName} Do\nQ\n`);
    beginObject(contentObjectId);
    push(`<< /Length ${contentBytes.length} >>\nstream\n`);
    push(contentBytes);
    push("endstream\nendobj\n");
  });

  const startXref = position;
  push(`xref\n0 ${objectCount + 1}\n0000000000 65535 f \n`);
  for (let index = 1; index <= objectCount; index += 1) {
    push(`${String(objectOffsets[index] || 0).padStart(10, "0")} 00000 n \n`);
  }
  push(`trailer\n<< /Size ${objectCount + 1} /Root 1 0 R >>\nstartxref\n${startXref}\n%%EOF`);
  return new Blob([concatUint8Arrays(chunks)], { type: "application/pdf" });
}

export async function exportBooksToPdf(books, title) {
  const rows = bookExportRows(books);
  const pageCanvases = renderPdfPages(rows, title);
  const pages = await Promise.all(
    pageCanvases.map(async (canvas) => ({
      width: canvas.width,
      height: canvas.height,
      bytes: await canvasToJpegBytes(canvas),
    })),
  );
  downloadBlob(buildPdfBlob(pages), `${slugifyFilename(title)}.pdf`);
}

