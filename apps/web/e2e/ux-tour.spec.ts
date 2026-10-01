import { test } from "@playwright/test";
import { DEMO, setTheme } from "./helpers";

/**
 * The 90-second tour (redesign brief): landing, sign-in, Home, the Room, battle podium, recap story.
 * Video lands in artifacts/ux/tour (not committed). Run with UX_TOUR=1.
 */
test.use({ viewport: { width: 1440, height: 900 }, video: { mode: "on", size: { width: 1440, height: 900 } } });
test.skip(process.env.UX_TOUR !== "1", "only on request");

test("ux tour", async ({ page }) => {
  test.setTimeout(240_000);
  await setTheme(page, "dark");
  const pause = (ms: number) => page.waitForTimeout(ms);

  // Landing: cover wall, then scroll the story chapters.
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await pause(3000);
  for (let i = 0; i < 9; i++) {
    await page.mouse.wheel(0, 650);
    await pause(1300);
  }

  // Sign-in: split screen with live art.
  await page.goto("/signin");
  await pause(1500);
  await page.getByLabel("Email").pressSequentially(DEMO.email, { delay: 35 });
  await page.getByLabel("Password", { exact: true }).pressSequentially(DEMO.password, { delay: 35 });
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/(home|onboarding)/);

  // Home: hero, shelves, friend activity.
  await page.waitForLoadState("networkidle");
  await pause(4000);
  await page.mouse.wheel(0, 700);
  await pause(2500);
  await page.mouse.wheel(0, -700);
  await pause(1000);

  // Command palette.
  await page.keyboard.press("Control+k");
  await pause(600);
  await page.keyboard.type("Aanya", { delay: 60 });
  await pause(1800);
  await page.keyboard.press("Escape");

  // The Room.
  await page.goto("/blends");
  await pause(1500);
  await page.getByRole("button", { name: "Listen together" }).click();
  await page.getByRole("dialog", { name: "Listen together" }).getByRole("button", { name: "Start session" }).click();
  await page.waitForURL(/\/sessions\//);
  for (const q of ["Kesariya", "Blinding Lights", "Levitating"]) {
    await page.getByLabel("Find a song").pressSequentially(q, { delay: 40 });
    await page.getByRole("list", { name: "Search results" }).getByRole("button", { name: "Add" }).first().click();
    await page.getByLabel("Find a song").fill("");
    await pause(700);
  }
  await page.getByRole("button", { name: "Play next" }).click();
  await pause(5000);
  await page.getByRole("button", { name: "Leave" }).click();
  await page.waitForURL(/\/blends$/);

  // Rituals: battle podium, then the recap story.
  await page.goto("/rituals");
  await page.waitForLoadState("networkidle");
  await pause(4000);
  await page.goto("/rituals?story=1#recap");
  await pause(14000);
});
