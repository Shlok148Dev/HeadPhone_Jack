import { expect, test } from "@playwright/test";
import { expectNoA11yViolations, signIn } from "../helpers";

/** EP-15 Song of the Week / Artist of the Week on Home (JNG-15-01/02, D-CHART-01..04). Read-only. */
test("Home shows this week's top 5 songs and artists among your people", async ({ page }) => {
  await signIn(page);
  const songs = page.getByRole("region", { name: "What your people played most" });
  await songs.scrollIntoViewIfNeeded();
  await expect(songs).toBeVisible();
  await expect(songs.getByText("#1", { exact: true })).toBeVisible();
  // #2–#5 as an ordered list with full, spoken labels.
  const rows = songs.getByRole("list", { name: "Songs 2 to 5" }).getByRole("listitem");
  await expect(rows).toHaveCount(4);
  await expect(rows.first()).toHaveAttribute("aria-label", /^Number 2, .+ by .+, (new this week|no change|up \d+|down \d+), played by \d+ friends?$/);
  // Tune in on #1 is honest about exact vs search, and visible (not text-on-same-colour).
  const tune = songs.getByRole("link", { name: /^(Play|Find) in (Spotify|Apple Music|YouTube Music|Amazon Music): / }).first();
  await expect(tune).toBeVisible();
  await expect(tune).toContainText(/(Play|Find) in/);

  const artists = page.getByRole("region", { name: /can.t stop playing/ });
  await expect(artists).toBeVisible();
  await expect(artists.getByRole("list", { name: "Artists 2 to 5" }).getByRole("listitem")).toHaveCount(4);
  await expectNoA11yViolations(page);
});

/** JNG-15-03/04: the Monday reveal plays #5 → #1 once, and the share card exports a real PNG. */
test("Monday reveal counts down to #1 and the share card downloads", async ({ page }) => {
  test.setTimeout(90_000);
  await signIn(page);
  await page.goto("/home?reveal=1"); // the notification's link starts the countdown
  const reveal = page.getByRole("region", { name: /Your people's Song of the Week/ });
  await reveal.scrollIntoViewIfNeeded();
  await expect(reveal.getByText("#1", { exact: true })).toBeVisible({ timeout: 10_000 });
  await expect(reveal.getByRole("list", { name: "Songs 2 to 5" }).getByRole("listitem")).toHaveCount(4);
  // #1 stays on screen after the countdown (marking it seen must not yank it away) until Done.
  await page.waitForTimeout(2500);
  await expect(reveal.getByText("#1", { exact: true })).toBeVisible();
  await reveal.getByRole("button", { name: "Done" }).click();
  await expect(page.getByRole("region", { name: /Your people's Song of the Week/ })).toHaveCount(0);
  // Seen server-side: on reload there's no reveal, and "Last week's #1" sits in the header instead.
  await page.goto("/home");
  const sotw = page.getByRole("region", { name: "What your people played most" });
  await sotw.scrollIntoViewIfNeeded();
  await expect(sotw.getByText(/^Last week's #1: /)).toBeVisible();
  await expect(page.getByRole("region", { name: /Your people's Song of the Week/ })).toHaveCount(0);

  const download = page.waitForEvent("download");
  await sotw.getByRole("button", { name: "Share" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("jingle-song-of-the-week.png");
  const path = await file.path();
  const fs = await import("node:fs");
  expect(fs.statSync(path!).size).toBeGreaterThan(50_000); // a real image with covers, not a blank canvas
});
