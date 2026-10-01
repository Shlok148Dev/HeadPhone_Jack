import { test } from "@playwright/test";
import { setTheme, signIn, snap } from "./helpers";

/** Definition of Done: every changed screen, both themes, 1440 and 390 px (artifacts/screenshots/s1). */
const WIDTHS = [
  { w: 1440, h: 900 },
  { w: 390, h: 844 },
];

for (const theme of ["dark", "light"] as const) {
  for (const { w, h } of WIDTHS) {
    test(`screens ${theme} ${w}`, async ({ page }) => {
      test.setTimeout(240_000);
      await page.setViewportSize({ width: w, height: h });
      await setTheme(page, theme);
      for (const [name, path] of [
        ["landing", "/"],
        ["signup", "/signup"],
        ["signin", "/signin"],
      ] as const) {
        await page.goto(path);
        await page.waitForLoadState("networkidle");
        await snap(page, `${name}-${theme}-${w}`);
      }
      await signIn(page);
      for (const [name, path] of [
        ["home", "/home"],
        ["onboarding-sources", "/onboarding/sources"],
        ["settings-connections", "/settings/connections"],
        ["connect-companion", "/connect/companion"],
        ["friends", "/friends?tab=friends"],
        ["friends-find", "/friends?tab=find"],
        ["friends-suggestions", "/friends?tab=suggestions"],
        ["settings-privacy", "/settings/privacy"],
        ["onboarding-friends", "/onboarding/friends"],
        ["circles", "/circles"],
        ["inbox", "/inbox"],
        ["inbox-sent", "/inbox?tab=sent"],
        ["blends", "/blends"],
        ["profile-me", "/u/demo"],
        ["profile-friend", "/u/aanya"],
        ["rituals", "/rituals"],
        ["notifications", "/notifications"],
        ["settings-notifications", "/settings/notifications"],
        ["settings-account", "/settings/account"],
      ] as const) {
        await page.goto(path);
        await page.waitForTimeout(3500);
        await snap(page, `${name}-${theme}-${w}`);
      }
      await page.goto("/circles");
      await page.getByRole("link", { name: /KJ Somaiya crew/ }).click();
      await page.waitForTimeout(3500);
      await snap(page, `circle-${theme}-${w}`);
      await page.getByRole("button", { name: /^Send / }).first().click();
      await page.waitForTimeout(1500);
      await snap(page, `send-sheet-${theme}-${w}`);
      await page.keyboard.press("Escape");
      await page.goto("/blends");
      await page.getByRole("link", { name: /Demo \+ Aanya \+ Kabir/ }).click();
      await page.waitForTimeout(2500);
      await snap(page, `blend-${theme}-${w}`);
      await page.goto("/blends");
      await page.getByRole("button", { name: "Listen together" }).click();
      await page.getByRole("dialog", { name: "Listen together" }).getByRole("button", { name: "Start session" }).click();
      await page.waitForURL(/\/sessions\//);
      await page.getByLabel("Find a song").fill("Kasoor");
      await page.getByRole("list", { name: "Search results" }).getByRole("button", { name: "Add" }).first().click();
      await page.waitForTimeout(2000);
      await snap(page, `session-${theme}-${w}`);
      await page.getByRole("button", { name: "Leave" }).click(); // last one out ends the room
    });
  }
}
