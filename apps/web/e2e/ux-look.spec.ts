import { test } from "@playwright/test";
import { setTheme, signIn } from "./helpers";

/** Design review captures (docs/ux/review): selected screens, both themes, desktop + mobile. */
const SCREENS = (process.env.UX_SCREENS ?? "/home").split(",");
for (const theme of ["dark", "light"] as const) {
  for (const { w, h } of [{ w: 1440, h: 900 }, { w: 390, h: 844 }]) {
    test(`ux ${theme} ${w}`, async ({ page }) => {
      test.setTimeout(180_000);
      await page.setViewportSize({ width: w, height: h });
      await setTheme(page, theme);
      if (process.env.UX_PUBLIC !== "1") await signIn(page);
      for (const path of SCREENS) {
        await page.goto(path);
        await page.waitForLoadState("networkidle");
        await page.waitForTimeout(1500);
        const name = path.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "landing";
        await page.screenshot({ path: `../../artifacts/ux/${name}-${theme}-${w}.png`, fullPage: process.env.UX_FULL === "1" });
      }
    });
  }
}

/** The Room: start a session, add a song, play it, capture (then leave: the room ends). */
test("ux room", async ({ page }) => {
  test.skip(process.env.UX_ROOM !== "1", "only on request");
  test.setTimeout(120_000);
  for (const theme of ["dark", "light"] as const) {
    await setTheme(page, theme);
    await page.setViewportSize({ width: 1440, height: 900 });
    await signIn(page);
    await page.goto("/blends");
    await page.getByRole("button", { name: "Listen together" }).click();
    await page.getByRole("dialog", { name: "Listen together" }).getByRole("button", { name: "Start session" }).click();
    await page.waitForURL(/\/sessions\//);
    for (const q of ["Kesariya", "Blinding Lights"]) {
      await page.getByLabel("Find a song").fill(q);
      await page.getByRole("list", { name: "Search results" }).getByRole("button", { name: "Add" }).first().click();
      await page.waitForTimeout(600);
    }
    await page.getByRole("button", { name: "Play next" }).click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `../../artifacts/ux/room-${theme}-1440.png` });
    await page.getByRole("button", { name: "Leave" }).click();
    await page.waitForURL(/\/blends$/);
  }
});
