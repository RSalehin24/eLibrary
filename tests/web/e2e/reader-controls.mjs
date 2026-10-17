export async function setReadingView(page, view) {
  await page.getByRole("button", { name: "Reading Settings", exact: true }).click();
  await page.getByLabel("Reading View", { exact: true }).selectOption(view);
  await page.getByRole("dialog").getByRole("button", { name: "Close", exact: true }).click();
}

export async function increaseTextSize(page) {
  await page.getByRole("button", { name: "Reading Settings", exact: true }).click();
  await page.getByRole("button", { name: "Increase Text Size", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Close", exact: true }).click();
}
