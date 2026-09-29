import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { ROUTE_WORDS, expectNoA11yViolations } from "../helpers";

const TAKEOUT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../services/ingest_ml/tests/fixtures/takeout/watch-history.json");

test.describe("JNG-01-14 one button per platform (+ JNG-01-06 import, JNG-01-09 unlink)", () => {
  test("Connect YouTube Music: consent, browser steps, history import, disconnect", async ({ page }) => {
    test.setTimeout(120_000);
    const id = Date.now().toString(36);
    await page.goto("/signup");
    await page.getByLabel("Email").fill(`connect-${id}@jingle.local`);
    await page.getByLabel("Password", { exact: true }).fill("e2e-password-123");
    await page.getByLabel("Username").fill(`c_${id}`.slice(0, 20));
    await page.getByLabel("Birth year").selectOption("1999");
    await page.getByLabel(/I agree/).check();
    await page.getByRole("button", { name: "Create account" }).click();
    await page.waitForURL(/\/onboarding\/sources/);

    // No route words on the platform cards (BR-14).
    await expect(page.locator("main")).not.toContainText(ROUTE_WORDS);
    await page.getByRole("button", { name: "Connect YouTube Music" }).click();
    const sheet = page.getByRole("dialog", { name: "Connect YouTube Music" });

    // Collecting plays needs explicit consent first (NFR-PRIV-01).
    await sheet.getByRole("checkbox").check();
    await sheet.getByRole("button", { name: "Continue" }).click();
    await expect(sheet.getByText("Install the Jingle Companion for your browser")).toBeVisible();
    await expectNoA11yViolations(page);

    await sheet.getByText("Other ways to connect").click();
    await sheet.getByLabel("Choose your watch history file").setInputFiles(TAKEOUT);
    // Success shows either the import result or, once the platform is live, "First play seen ✓".
    await expect(sheet.getByText(/Imported 2 plays from YouTube Music|First play seen ✓/)).toBeVisible({ timeout: 30_000 });
    await sheet.getByRole("button", { name: /Skip for now|Done/ }).click();

    await page.goto("/settings/connections");
    const row = page.getByRole("listitem").filter({ hasText: "YouTube Music" });
    await expect(row.getByText("Connected", { exact: true })).toBeVisible();
    await row.getByRole("button", { name: "Disconnect" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Disconnect" }).click();
    await expect(row.getByText("Disconnected", { exact: true })).toBeVisible();
  });

  test("Spotify without keys falls back to the browser path, never an error (BR-15)", async ({ page }) => {
    const id = Date.now().toString(36);
    await page.goto("/signup");
    await page.getByLabel("Email").fill(`sp-${id}@jingle.local`);
    await page.getByLabel("Password", { exact: true }).fill("e2e-password-123");
    await page.getByLabel("Username").fill(`s_${id}`.slice(0, 20));
    await page.getByLabel("Birth year").selectOption("1999");
    await page.getByLabel(/I agree/).check();
    await page.getByRole("button", { name: "Create account" }).click();
    await page.waitForURL(/\/onboarding\/sources/);
    await page.getByRole("button", { name: "Connect Spotify" }).click();
    const sheet = page.getByRole("dialog", { name: "Connect Spotify" });
    await sheet.getByRole("checkbox").check();
    await sheet.getByRole("button", { name: "Continue" }).click();
    await expect(sheet.getByRole("link", { name: "Connect this browser" })).toBeVisible();
    await expect(sheet.getByText(/couldn't connect/i)).toHaveCount(0);
  });
});
