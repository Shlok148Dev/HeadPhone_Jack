import { expect, test } from "@playwright/test";
import { ROUTE_WORDS, expectNoA11yViolations, signIn } from "../helpers";

test.describe("JNG-05-01 my own card", () => {
  test("Home shows my card with platform and freshness, never a route", async ({
    page,
  }) => {
    await signIn(page);
    await expect(
      page.getByRole("heading", { name: "You right now" }),
    ).toBeVisible();
    // Demo mode backfills history, so a real label is shown ("Live on …", "… ago on …").
    const label = page
      .getByText(/^(Live|Just now|Recently|\d+ (min|h|d) ago)( on .+)?$/)
      .first();
    await expect(label).toBeVisible({ timeout: 20_000 });
    await expect(page.locator("main")).not.toContainText(ROUTE_WORDS);
    await expectNoA11yViolations(page);
  });

  test("Settings → Connections shows all four apps, one tap each", async ({
    page,
  }) => {
    await signIn(page);
    await page.goto("/settings/connections");
    const apps = page.getByRole("list", { name: "Music apps" });
    for (const name of [
      "Spotify",
      "Apple Music",
      "YouTube Music",
      "Amazon Music",
    ]) {
      await expect(
        apps.getByRole("button", { name: new RegExp(name) }),
      ).toBeVisible();
    }
    await expectNoA11yViolations(page);
  });
});
