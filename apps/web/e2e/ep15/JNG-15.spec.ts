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
