import { expect, test } from "@playwright/test";
import { expectNoA11yViolations, signIn } from "../helpers";

test.describe("EP-04 circles", () => {
  test("JNG-04-01 create, JNG-04-02 link join, JNG-04-03/06 hand over and leave", async ({ page, browser, request }) => {
    const id = Date.now().toString(36);
    const username = `crc_${id}`.slice(0, 20);
    const email = `${username}@jingle.local`;
    const password = "e2e-password-123";
    const reg = await request.post("/api/v1/auth/register", {
      data: { email, password, username, display_name: "Circle Joiner", birth_year: 1998 },
    });
    expect(reg.ok()).toBeTruthy();

    await signIn(page);
    await page.goto("/circles");
    await expect(page.getByRole("heading", { name: "Circles", level: 1 })).toBeVisible();
    await expectNoA11yViolations(page);
    await page.getByRole("button", { name: "New circle" }).first().click();
    const name = `E2E crew ${id}`;
    await page.getByLabel("Circle name").fill(name);
    await page.getByRole("button", { name: "Create circle" }).click();
    await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();

    // Created with ?invite=1: the invite sheet opens; make a 7-day link.
    const sheet = page.getByRole("dialog", { name: `Invite to ${name}` });
    await sheet.getByRole("button", { name: "Make a link" }).click();
    const url = await sheet.getByLabel("Circle invite link").inputValue();
    const path = new URL(url).pathname;
    expect(path).toMatch(/^\/circles\/join\//);
    await sheet.getByRole("button", { name: "Close" }).click();

    // The joiner opens the link and taps Join themselves (BR-08).
    const other = await browser.newContext();
    const p2 = await other.newPage();
    await signIn(p2, email, password);
    await p2.goto(path);
    await expect(p2.getByRole("heading", { name: `Join ${name}` })).toBeVisible();
    await expectNoA11yViolations(p2);
    await p2.getByRole("button", { name: "Join circle" }).click();
    await p2.waitForURL(/\/circles\/[0-9a-f-]{36}$/);
    await expect(p2.getByRole("heading", { name, level: 1, exact: true })).toBeVisible();
    await other.close();

    await page.reload();
    const row = page.getByRole("listitem").filter({ hasText: `@${username}` });
    await expect(row).toBeVisible();
    await expectNoA11yViolations(page);

    // The owner can't just leave a circle with people in it.
    await page.getByRole("button", { name: "Leave" }).click();
    await expect(page.getByRole("dialog", { name: "Hand it over first" })).toBeVisible();
    await page.getByRole("button", { name: "Got it" }).click();

    await row.getByRole("button", { name: "Options for Circle Joiner" }).click();
    await page.getByRole("button", { name: "Make owner" }).click();
    await expect(row.getByText("Owner")).toBeVisible();

    await page.getByRole("button", { name: "Leave" }).click();
    await page.getByRole("dialog", { name: `Leave ${name}?` }).getByRole("button", { name: "Leave" }).click();
    await page.waitForURL(/\/circles$/);
    await expect(page.getByRole("link", { name: new RegExp(name) })).toHaveCount(0);
  });

  test("an expired or unknown circle link says so", async ({ page }) => {
    await signIn(page);
    await page.goto("/circles/join/not-a-real-token");
    await expect(page.getByRole("heading", { name: /doesn.t work any more/ })).toBeVisible();
  });

  test("JNG-05-03 a circle's page shows only that circle's listening", async ({ page }) => {
    // Home no longer has circle chips (D-HOME-02); the circle page is where a circle's feed lives.
    await signIn(page);
    await page.goto("/circles");
    await page.getByRole("link", { name: /KJ Somaiya crew/ }).first().click();
    await expect(page.getByRole("article", { name: /Aanya/ }).first()).toBeVisible();
    await expect(page.getByRole("article", { name: /Zoya/ })).toHaveCount(0); // Zoya isn't in this circle
  });
});

test("JNG-04-08 circle playlist: add a song credited to you, then remove it", async ({ page }) => {
  await signIn(page);
  await page.goto("/circles");
  await page.getByRole("link", { name: /KJ Somaiya crew/ }).first().click();
  await page.getByRole("link", { name: /^Playlist/ }).click();
  await page.waitForURL(/\/playlist$/);
  await expect(page.getByRole("heading", { name: "Circle playlist" })).toBeVisible();
  const list = page.getByRole("list", { name: "Songs in the playlist" });
  // Every song shows who added it.
  await expect(list.getByRole("listitem").first()).toHaveAttribute("aria-label", /, added by .+ ago|just now/);
  await page.getByLabel("Search a song or artist").fill("Blinding Lights");
  await page.getByRole("list", { name: "Search results", exact: true }).getByRole("button").first().click();
  await page.getByLabel("A line about it (optional)").fill("e2e pick");
  await page.getByRole("button", { name: "Add to playlist" }).click();
  const mine = list.getByRole("listitem", { name: /Blinding Lights by .+, added by you/ });
  await expect(mine).toBeVisible();
  await expect(mine).toContainText("e2e pick");
  await mine.getByRole("button", { name: /Remove Blinding Lights/ }).click();
  await expect(list.getByRole("listitem", { name: /Blinding Lights by .+, added by you/ })).toHaveCount(0);
});

test("JNG-04-09 play the playlist in order: your app first, honest when an app isn't set up", async ({ page }) => {
  await signIn(page);
  await page.goto("/circles");
  await page.getByRole("link", { name: /KJ Somaiya crew/ }).first().click();
  await page.getByRole("link", { name: /^Playlist$/ }).click(); // no song count on the button
  await page.waitForURL(/\/playlist$/);
  const play = page.getByRole("button", { name: /^(Play|Update & play) in (Spotify|Apple Music|YouTube Music|Amazon Music)$/ });
  await expect(play).toBeVisible();
  await page.getByRole("button", { name: "Other apps" }).click();
  await page.getByRole("menuitem", { name: /in Amazon Music$/ }).click();
  const dialog = page.getByRole("dialog", { name: "Not available in Amazon Music yet" });
  await expect(dialog).toContainText("doesn't let other apps create playlists");
  await dialog.getByRole("button", { name: "Got it" }).click();
  // Without keys in .env the primary app explains instead of failing.
  await play.click();
  await expect(page.getByRole("dialog", { name: /Not available in .+ yet/ })).toContainText("isn't switched on for this Jingle yet");
});
