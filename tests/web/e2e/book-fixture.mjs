import { randomUUID } from "node:crypto";
import { expect, fixture, useAccount } from "./fixtures.mjs";

export async function newDigitalBook(page) {
  await useAccount(page, "administrator");
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  const response = await page.request.post("/api/v1/manage/books/", {
    headers: { "X-CSRFToken": session.csrf_token },
    data: { operation_id: randomUUID(), title: `আপলোডের পরীক্ষা ${randomUUID()}` },
  });
  expect(response.status()).toBe(201);
  return response.json();
}

export async function readingEPUB(page) {
  const response = await page.request.get(`/api/v1/reading/books/${encodeURIComponent(fixture.upload_book.slug)}/download/`);
  expect(response.status()).toBe(200);
  const bytes = await response.body(), comment = Buffer.from(randomUUID());
  const end = bytes.lastIndexOf(Buffer.from("504b0506", "hex"));
  expect(end).toBeGreaterThan(0);
  expect(end + 22 + bytes.readUInt16LE(end + 20)).toBe(bytes.length);
  // A unique ZIP comment exercises preparation instead of reusing the seeded checksum.
  const archive = Buffer.concat([bytes.subarray(0, end + 22), comment]);
  archive.writeUInt16LE(comment.length, end + 20);
  return archive;
}
