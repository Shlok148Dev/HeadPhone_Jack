import { expect, test } from "@playwright/test";
import { expectNoA11yViolations, ROUTE_WORDS, signIn } from "../helpers";

test.describe("EP-06 sends and mixtapes", () => {
  test("JNG-06-07 inbox shows received sends; JNG-06-03 opens on my app; JNG-06-06 react", async ({ page }) => {
    await signIn(page);
    await page.goto("/inbox");
    await expect(page.getByRole("heading", { name: "Inbox", level: 1 })).toBeVisible();
    const row = page.getByRole("listitem", { name: "Kasoor from Aanya" });
    await expect(row).toBeVisible();
    await expect(row.getByRole("link", { name: /^(Open|Search) in / })).toBeVisible();
    await expect(page.getByRole("listitem", { name: "Mixtape from Kabir" })).toBeVisible();
    await expect(page.locator("main")).not.toContainText(ROUTE_WORDS);
    await expectNoA11yViolations(page);

    await row.getByRole("button", { name: "React" }).click();
    const dialog = page.getByRole("dialog", { name: "React to Aanya" });
    const fire = dialog.getByRole("button", { name: "🔥" });
    const wasOn = (await fire.getAttribute("aria-pressed")) === "true";
    await fire.click();
    await expect(row.getByText("You reacted 🔥")).toHaveCount(wasOn ? 0 : 1);
  });

  test("JNG-06-01 send a song from a card; JNG-06-04 Sent shows status", async ({ page }) => {
    await signIn(page);
    await page.goto("/home");
    await page.getByRole("button", { name: /^Send / }).first().click();
    const sheet = page.getByRole("dialog", { name: "Send a song" });
    await expect(sheet).toBeVisible();
    await expect(sheet.getByText("Pick at least one friend or circle")).toBeVisible();
    await sheet.getByLabel("Send to").fill("zoy");
    await sheet.getByRole("button", { name: "Zoya", exact: true }).click();
    const note = `e2e ${Date.now().toString(36)}`;
    await sheet.getByLabel("Note (optional)").fill(note);
    await expectNoA11yViolations(page);
    await sheet.getByRole("button", { name: "Send", exact: true }).click();
    await expect(page.getByText("Sent to Zoya")).toBeVisible();

    await page.goto("/inbox?tab=sent");
    const sent = page.getByRole("listitem").filter({ hasText: note });
    await expect(sent).toBeVisible();
    await expect(sent.getByRole("list", { name: /Status for Zoya: (Sent|Delivered|Viewed|Played)/ })).toBeVisible();
    await expectNoA11yViolations(page);
  });

  test("JNG-06-02 mixtape needs 5–8 songs", async ({ page }) => {
    await signIn(page);
    await page.goto("/inbox");
    await page.getByRole("button", { name: "Send a song" }).first().click();
    const sheet = page.getByRole("dialog", { name: "Send a mixtape" });
    for (const q of ["Kesariya", "Tum Hi Ho", "Kasoor", "Excuses", "Lover"]) {
      await sheet.getByLabel("Find a song").fill(q);
      await sheet.getByRole("list", { name: "Search results" }).getByRole("button", { name: "Add" }).first().click();
    }
    await expect(sheet.getByText("5/8 songs")).toBeVisible();
    await sheet.getByLabel("Send to").fill("aany");
    await sheet.getByRole("button", { name: "Aanya", exact: true }).click();
    await expect(sheet.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
    await sheet.getByRole("button", { name: /^Remove / }).first().click();
    await expect(sheet.getByText("Add at least 5 songs, or remove extras to send one song")).toBeVisible();
    await expect(sheet.getByRole("button", { name: "Send", exact: true })).toBeDisabled();
  });
});
