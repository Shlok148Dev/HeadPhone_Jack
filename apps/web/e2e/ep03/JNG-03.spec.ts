import { expect, test } from "@playwright/test";
import { expectNoA11yViolations, signIn } from "../helpers";

test("JNG-03-01/05 suggestions show reasons; add and dismiss remove them", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page);
  await page.goto("/friends?tab=suggestions");
  // Demo world: Kiara and Rohan are friends of friends; Maya shares taste. Computed by the worker.
  const cards = page.getByRole("article", { name: /^Suggestion: / });
  await expect(cards.first()).toBeVisible({ timeout: 90_000 });
  await expect(cards.first().getByRole("list", { name: "Why we suggest them" })).toBeVisible();
  await expectNoA11yViolations(page);

  const count = await cards.count();
  await cards.first().getByRole("button", { name: "Add" }).click();
  await expect(page.getByText("Request sent")).toBeVisible();
  await expect(cards).toHaveCount(count - 1);
  if (count > 1) {
    await cards.first().getByRole("button", { name: /^Dismiss / }).click();
    await expect(cards).toHaveCount(count - 2);
  }
});
