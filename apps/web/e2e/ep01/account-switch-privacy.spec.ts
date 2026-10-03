import { expect, test } from "@playwright/test";
import { signIn } from "../helpers";

/**
 * Privacy regression (founder report, 2026-10-03): after signing out of one account and creating
 * another in the same tab (client-side navigation only, no reload), nothing cached for the first
 * person may show for the second. A brand-new account's Home is "Get started", with no charts.
 */
test("a new account in the same tab never sees the previous account's data", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await signIn(page); // demo account: has friends, charts, a feed
  await expect(
    page.getByRole("region", { name: "What your people played most" }),
  ).toBeVisible({ timeout: 20_000 });

  // Sign out and sign up again without ever reloading the page.
  await page.getByRole("button", { name: "Sign out" }).first().click();
  await page.waitForURL(/\/(signin|$)/);
  await page.locator('a[href="/signup"]').first().click();
  await page.waitForURL(/\/signup/);
  const id = `sw${Date.now().toString(36)}`;
  await page.getByLabel("Email").fill(`${id}@jingle.local`);
  await page.getByLabel("Password", { exact: true }).fill("e2e-password-123");
  await page.getByLabel("Username").fill(id);
  await page.getByLabel("Birth year").selectOption("1999");
  await page.getByLabel(/I agree/).check();
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL(/\/onboarding\/sources/);
  await page.getByRole("button", { name: "Skip for now" }).click();
  await page.waitForURL(/\/onboarding\/privacy/);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.waitForURL(/\/onboarding\/friends/);
  await page.getByRole("button", { name: "Go to my feed" }).click();
  await page.waitForURL(/\/home/);

  const main = page.locator("main");
  await expect(
    main.getByRole("heading", { name: "Get started" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "What your people played most" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: /can.t stop playing/ }),
  ).toHaveCount(0);
  await expect(main).not.toContainText(
    /Song of the Week|Artist of the Week|warming up/,
  );
  // The demo account's name and friends must not appear anywhere on the new account's Home.
  await expect(main).not.toContainText(/Aanya|Kabir|Demo \+/);
});
