import { expect, test } from "@playwright/test";
import { signIn } from "../helpers";

/** JNG-06 on Home: "Sent to you" cards open the exact send, carry Tune in, and mark New/Played honestly. */
test("Sent to you opens the exact send and offers Tune in", async ({ page }) => {
  await signIn(page);
  const shelf = page.locator("section").filter({ has: page.getByRole("heading", { name: /Sent to you/ }) });
  await expect(shelf).toBeVisible();
  // Tune in on the card itself: exact links say Play, searches say Find.
  await expect(shelf.getByRole("link", { name: /^(Play|Find) in (Spotify|Apple Music|YouTube Music|Amazon Music): / }).first()).toBeVisible();
  const card = shelf.locator('a[href^="/inbox?item="]').first();
  const href = await card.getAttribute("href");
  const id = decodeURIComponent(href!.split("item=")[1]!);
  await card.click();
  await page.waitForURL(/\/inbox\?item=/);
  const row = page.locator(`#send-${id}`);
  await expect(row).toBeVisible();
  await expect(row).toHaveClass(/brand-violet/); // highlighted on arrival
});
