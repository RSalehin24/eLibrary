import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";

test("administrators land in Admin and switch to a personal reader view using the same account", async ({ page }) => {
  await page.goto("/login/");
  await page.getByLabel("ইমেইল", { exact:true }).fill(fixture.administrator.email);
  await page.getByLabel("পাসওয়ার্ড", { exact:true }).fill(fixture.administrator.password);
  await page.getByRole("button", { name:"প্রবেশ করুন", exact:true }).click();
  await expect(page).toHaveURL(/\/manage\/sources\/$/);
  const original=await (await page.request.get("/api/v1/auth/session/")).json();
  await page.locator(".admin-topbar").getByRole("link", { name:"পাঠকের ভিউ", exact:true }).click();
  await expect(page).toHaveURL(/\/my-books\/$/);
  const header=page.locator(".site-header");
  await expect(header).toHaveAttribute("data-workspace","reader");
  await expect(header.getByRole("navigation").getByRole("link", { name:"আমার বই", exact:true })).toBeVisible();
  await expect(header.locator('nav a[href^="/manage/"]')).toHaveCount(0);
  await expect(page.locator(".catalog-management-shortcut")).toHaveCount(0);
  await header.locator(".account-menu > summary").click();
  await header.getByRole("link", { name:"প্রোফাইল", exact:true }).click();
  await expect(page.getByRole("heading", { name:"প্রোফাইল ও নিরাপত্তা", exact:true })).toBeVisible();
  await expect(page.getByRole("link", { name:"অ্যাডমিন প্যানেল", exact:true })).toHaveCount(0);
  await page.reload(); await expect(page.locator(".site-header")).toHaveAttribute("data-workspace","reader");
  const current=await (await page.request.get("/api/v1/auth/session/")).json();
  expect(current.user.id).toBe(original.user.id); expect(current.workspaces.manage).toBe(true);
  await page.getByRole("link", { name:"অ্যাডমিনে ফিরুন", exact:true }).click();
  await expect(page).toHaveURL(/\/manage\/sources\/$/);
  await page.locator(".admin-topbar").getByRole("link",{ name:"পাঠকের ভিউ",exact:true }).click();
  await expect(page.locator(".site-header")).toHaveAttribute("data-workspace","reader");
});

test("reader accounts cannot obtain management navigation through a view preference", async ({ page }) => {
  await useAccount(page,"reader");
  await page.context().addCookies([{name:"library-workspace-view",value:`${fixture.reader.id}:admin`,url:process.env.FOUNDATION_WEB_URL ?? "http://127.0.0.1:3000"}]);
  await page.goto("/profile/");
  await expect(page.locator(".site-header")).toHaveAttribute("data-workspace","reader");
  await expect(page.getByRole("link",{name:"অ্যাডমিনে ফিরুন",exact:true})).toHaveCount(0);
  expect((await page.request.get("/manage/")).status()).toBe(404);
  await page.goto("/login/"); await expect(page).toHaveURL(/\/my-books\/$/);
});

test("the active admin section stays visible when long labels grow without a viewport change", async ({ page }) => {
  await useAccount(page,"administrator");
  await page.setViewportSize({width:320,height:900});
  await page.goto("/manage/entities/");
  await setLanguage(page, "en");
  await page.evaluate(()=>document.fonts.ready);
  await page.getByRole("button", { name:"Open menu", exact:true }).click();
  const navigation=page.locator(".admin-navigation-drawer nav"), current=navigation.locator('[aria-current="page"]');
  await expect(current).toHaveText("Authors & Categories");
  await page.addStyleTag({content:"html {font-size:200%}"});
  await expect.poll(async()=>{
    const link=await current.boundingBox(), container=await navigation.boundingBox();
    return link.x>=container.x-1 && link.x+link.width<=container.x+container.width+1;
  }).toBe(true);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test("headers preserve the Bengali wordmark and single-line navigation across viewport sizes", async ({ page }) => {
  await useAccount(page,"administrator"); await page.goto("/profile/");
  for(const language of ["bn","en"]) {
    if(language==="en") await setLanguage(page, "en");
    for(const width of [320,390,768,820,1024,1100,1280,1366,1920]) {
      await page.setViewportSize({width,height:900}); await page.evaluate(()=>document.fonts.ready);
      const header=page.locator(".site-header"); await expect(header.getByRole("img",{name:"বাংলা পাঠাগার",exact:true})).toBeVisible();
      const wordmark=await header.locator(".brand-logo text").evaluate(node=>{const box=node.getBBox();return {right:box.x+box.width,bottom:box.y+box.height};});
      expect(wordmark.right).toBeLessThanOrEqual(236); expect(wordmark.bottom).toBeLessThanOrEqual(52);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
      for(const link of await header.locator("nav a").all()) expect((await link.boundingBox()).height).toBeLessThanOrEqual(60);
      const last=header.locator("nav a").last(); await last.focus();
      const linkBox=await last.boundingBox(), navBox=await header.locator("nav").boundingBox();
      expect(linkBox.x+linkBox.width).toBeLessThanOrEqual(navBox.x+navBox.width+1);
      if([390,1366].includes(width)) await page.screenshot({path:`test-artifacts/foundation/ui-header-admin-${language}-${width}.png`});
    }
  }
});
