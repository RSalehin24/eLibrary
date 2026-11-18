export async function processingRequest(page, path, { method = "GET", body } = {}) {
  const result = await page.evaluate(
    async ({ requestPath, requestMethod, requestBody }) => {
      const response = await fetch(`/api${requestPath}`, {
        method: requestMethod,
        cache: "no-store",
        credentials: "include",
        headers: {
          Accept: "application/json",
          ...(requestMethod === "GET"
            ? {}
            : {
                "Content-Type": "application/json",
                "X-CSRFToken":
                  decodeURIComponent(
                    document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || "",
                  ) || "",
              }),
        },
        body:
          requestMethod === "GET" || requestBody === undefined
            ? undefined
            : JSON.stringify(requestBody),
      });
      const text = await response.text();
      return {
        ok: response.ok,
        status: response.status,
        text,
      };
    },
    {
      requestPath: path,
      requestMethod: method,
      requestBody: body,
    },
  );

  if (!result.ok) {
    throw new Error(
      `Processing API ${path} failed with ${result.status}: ${result.text}`,
    );
  }

  return result.text ? JSON.parse(result.text) : null;
}

export async function processingGet(page, path) {
  return processingRequest(page, path);
}

export async function processingPost(page, path, body = {}) {
  await page.evaluate(async () => {
    await fetch("/api/csrf/", { credentials: "include" });
  });
  return processingRequest(page, path, {
    method: "POST",
    body,
  });
}

export async function processingCard(page, card) {
  return processingGet(
    page,
    `/processing/card/?${new URLSearchParams({ card }).toString()}`,
  );
}

export async function processingTable(page, card, params = {}) {
  const search = new URLSearchParams({ card, limit: "60" });
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  return processingGet(page, `/processing/table/?${search.toString()}`);
}
