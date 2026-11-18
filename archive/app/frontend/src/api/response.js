export async function parseResponse(response) {
  if ([204, 205].includes(response.status)) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

export function filenameFromDisposition(headerValue) {
  if (!headerValue) {
    return "";
  }

  const utf8Match = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) {
    return decodeURIComponent(utf8Match[1]);
  }

  const plainMatch = headerValue.match(/filename="?([^"]+)"?/i);
  return plainMatch ? plainMatch[1] : "";
}

export function fallbackDownloadFilename(contentType) {
  if (contentType.includes("application/pdf")) {
    return "download.pdf";
  }
  if (contentType.includes("text/csv")) {
    return "download.csv";
  }
  return "download";
}
