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

/** JNG-15-03/04: the reveal sits at the top, counts down only once visible, stays until Done, can be
 * replayed, and the share card exports a real PNG. */
test("Monday reveal: top of Home, counts down when visible, replayable; share card downloads", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page);
  await page.goto("/home?reveal=1"); // the notification's link
  const reveal = page.getByRole("region", { name: /Your people's Song of the Week/ });
  await expect(reveal).toBeVisible();
  // It is the first section on Home (above the Now stage) while waiting.
  const order = await page.locator("main section[aria-labelledby]").evaluateAll((els) => els.map((e) => e.getAttribute("aria-labelledby")));
  expect(order[0]).toBe("reveal-h");
  // A real countdown: #1 is not there at first, then lands and stays.
  await expect(reveal.getByText("#1", { exact: true })).toHaveCount(0);
  await expect(reveal.getByText("#1", { exact: true })).toBeVisible({ timeout: 10_000 });
  await page.waitForTimeout(1500);
  await expect(reveal.getByText("#1", { exact: true })).toBeVisible();
  await reveal.getByRole("button", { name: "Done" }).click();
  await expect(page.getByRole("region", { name: /Your people's Song of the Week/ })).toHaveCount(0);

  // Seen server-side: on reload no reveal; "Last week's #1 · Replay" instead, and Replay plays it again.
  await page.goto("/home");
  const sotw = page.getByRole("region", { name: "What your people played most" });
  await sotw.scrollIntoViewIfNeeded();
  const replay = sotw.getByRole("button", { name: /Last week.s #1: .+ Replay/ });
  await expect(replay).toBeVisible();
  await replay.click();
  const again = page.getByRole("region", { name: "Your people's Song of the Week" });
  await expect(again.getByText("#1", { exact: true })).toBeVisible({ timeout: 10_000 });
  await again.getByRole("button", { name: "Done" }).click();

  const download = page.waitForEvent("download");
  await sotw.getByRole("button", { name: "Share" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("jingle-song-of-the-week.png");
  const fs = await import("node:fs");
  expect(fs.statSync((await file.path())!).size).toBeGreaterThan(50_000); // covers drawn, not a blank canvas
});

test("with reduced motion the reveal still counts down, step by step", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await signIn(page);
  await page.goto("/home");
  const sotw = page.getByRole("region", { name: "What your people played most" });
  await sotw.scrollIntoViewIfNeeded();
  await sotw.getByRole("button", { name: /Replay/ }).click();
  const r = page.getByRole("region", { name: "Your people's Song of the Week" });
  await expect(r.getByText("#1", { exact: true })).toHaveCount(0); // not everything at once
  await expect(r.getByText("#1", { exact: true })).toBeVisible({ timeout: 10_000 });
});
