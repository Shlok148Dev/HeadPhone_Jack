import { expect, test } from "@playwright/test";
import { expectNoA11yViolations } from "../helpers";

test.describe("JNG-01-01 sign up with email", () => {
  test("Adult signs up and lands on onboarding sources", async ({ page }) => {
    const id = Date.now().toString(36);
    await page.goto("/signup");
    await expectNoA11yViolations(page);
    await page.getByLabel("Email").fill(`e2e-${id}@jingle.local`);
    await page.getByLabel("Password", { exact: true }).fill("e2e-password-123");
    await page.getByLabel("Username").fill(`e2e_${id}`.slice(0, 20));
    await page.getByLabel("Birth year").selectOption("2000");
    await page.getByLabel(/I agree/).check();
    await page.getByRole("button", { name: "Create account" }).click();
    await page.waitForURL(/\/onboarding\/sources/);
    await expect(page.getByRole("heading", { name: "Connect your music" })).toBeVisible();
  });

  test("Under-18 is refused and no account is created", async ({ page }) => {
    const id = Date.now().toString(36);
    await page.goto("/signup");
    await page.getByLabel("Email").fill(`kid-${id}@jingle.local`);
    await page.getByLabel("Password", { exact: true }).fill("e2e-password-123");
    await page.getByLabel("Username").fill(`kid_${id}`.slice(0, 20));
    await page.getByLabel("Birth year").selectOption(String(new Date().getFullYear() - 15));
    await page.getByLabel(/I agree/).check();
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Jingle is for people 18 and over for now.")).toBeVisible();
    await page.goto("/signin");
    await page.getByLabel("Email").fill(`kid-${id}@jingle.local`);
    await page.getByLabel("Password", { exact: true }).fill("e2e-password-123");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("That email and password don't match.")).toBeVisible();
  });
});
