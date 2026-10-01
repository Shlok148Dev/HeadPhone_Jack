import { expect, test } from "@playwright/test";
import { expectNoA11yViolations, signIn } from "../helpers";

test.describe("EP-08 understand", () => {
  test("JNG-08-01/02 friend profile shows a score only with its breakdown; sound unavailable", async ({ page }) => {
    await signIn(page);
    await page.goto("/u/aanya");
    await expect(page.getByRole("heading", { name: "You and Aanya" })).toBeVisible();
    await expect(page.getByText("Sound comparison unavailable")).toBeVisible();
    const ring = page.getByRole("img", { name: /Taste match \d+ out of 100/ });
    const limited = page.getByTestId("compat-limited");
    await expect(ring.or(limited)).toBeVisible({ timeout: 20_000 });
    if (await ring.isVisible()) await expect(page.getByText("Artists", { exact: true })).toBeVisible(); // BR-09
    await expectNoA11yViolations(page);
  });

  test("JNG-08-07 my stats or JNG-08-06 building state; JNG-08-03 timeline", async ({ page }) => {
    await signIn(page);
    await page.goto("/u/demo");
    const stats = page.getByRole("heading", { name: "Last 30 days" });
    const building = page.getByRole("heading", { name: "Your stats are on their way" });
    await expect(stats.or(building)).toBeVisible({ timeout: 20_000 });
    if (await stats.isVisible()) {
      await expect(page.getByText("Minutes listened")).toBeVisible();
      await expect(page.getByRole("heading", { name: "Your year in music" })).toBeVisible();
      await expect(page.getByRole("table", { name: "Plays per month" })).toBeAttached();
    }
    await expectNoA11yViolations(page);
  });
});
