import { expect, fixture } from "./fixtures.mjs";

export async function startSetup(page, account) {
  await page.getByRole("button", { name: "দুই ধাপের নিরাপত্তা চালু করুন", exact: true }).click();
  await page.getByLabel("পাসওয়ার্ড দিয়ে নিশ্চিত করুন", { exact: true }).fill(fixture[account].password);
  await page.getByRole("button", { name: "সেটআপ খুলুন", exact: true }).click();
  await expect(page.getByTestId("authenticator-secret")).toBeVisible();
  return (await page.getByTestId("authenticator-secret").textContent()).trim();
}
