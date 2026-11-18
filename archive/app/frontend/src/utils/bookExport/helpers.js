export function downloadBlob(blob, filename) {
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
}

export function slugifyFilename(value) {
  return (
    String(value || "books-export")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "books-export"
  );
}

export function escapeCsv(value) {
  const stringValue = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(stringValue) ? `"${stringValue.replace(/"/g, "\"\"")}"` : stringValue;
}

export function wrapLongToken(ctx, token, maxWidth) {
  const segments = [];
  let current = "";
  for (const character of token) {
    const candidate = `${current}${character}`;
    if (!current || ctx.measureText(candidate).width <= maxWidth) {
      current = candidate;
    } else {
      segments.push(current);
      current = character;
    }
  }
  if (current) {
    segments.push(current);
  }
  return segments;
}

export function wrapText(ctx, value, maxWidth) {
  const rawValue = String(value ?? "");
  const paragraphs = rawValue
    .split("\n")
    .map((paragraph) => paragraph.replace(/\s+/g, " ").trim())
    .filter((paragraph, index, collection) => paragraph || collection.length === 1);
  if (!paragraphs.length) {
    return [""];
  }

  const lines = [];
  paragraphs.forEach((paragraph) => {
    if (!paragraph) {
      lines.push("");
      return;
    }
    let currentLine = "";
    paragraph.split(" ").forEach((word) => {
      const candidate = currentLine ? `${currentLine} ${word}` : word;
      if (ctx.measureText(candidate).width <= maxWidth) {
        currentLine = candidate;
        return;
      }
      if (currentLine) {
        lines.push(currentLine);
        currentLine = "";
      }
      if (ctx.measureText(word).width <= maxWidth) {
        currentLine = word;
        return;
      }
      const pieces = wrapLongToken(ctx, word, maxWidth);
      lines.push(...pieces.slice(0, -1));
      currentLine = pieces.at(-1) || "";
    });
    if (currentLine) {
      lines.push(currentLine);
    }
  });

  return lines.length ? lines : [rawValue.trim()];
}

export function clampLineToWidth(ctx, line, maxWidth) {
  if (ctx.measureText(line).width <= maxWidth) {
    return line;
  }
  let nextLine = line;
  while (nextLine.length > 1 && ctx.measureText(`${nextLine}...`).width > maxWidth) {
    nextLine = nextLine.slice(0, -1);
  }
  return `${nextLine}...`;
}

export function clampLines(ctx, lines, maxLines, maxWidth) {
  if (lines.length <= maxLines) {
    return lines;
  }
  const truncated = lines.slice(0, maxLines);
  truncated[maxLines - 1] = clampLineToWidth(ctx, truncated[maxLines - 1], maxWidth);
  return truncated;
}

export function concatUint8Arrays(chunks) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const output = new Uint8Array(totalLength);
  let offset = 0;
  chunks.forEach((chunk) => {
    output.set(chunk, offset);
    offset += chunk.length;
  });
  return output;
}

