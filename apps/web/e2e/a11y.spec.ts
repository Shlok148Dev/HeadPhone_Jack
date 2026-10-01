import { expect, test, type Page } from "@playwright/test";
import { expectNoA11yViolations, signIn } from "./helpers";

/**
 * JNG-13-07 accessibility pass: axe (WCAG 2.2 AA) on every route in both themes, plus keyboard
 * basics — the skip link is the first stop and lands on <main>, and focus is always visible.
 */
const PUBLIC = ["/", "/signin", "/signup", "/design", "/invite/not-a-code", "/circles/join/not-a-token", "/recap/not-a-token"];
const SIGNED_IN = [
  "/home",
  "/friends?tab=friends",
  "/friends?tab=requests",
  "/friends?tab=suggestions",
  "/friends?tab=find",
  "/circles",
  "/blends",
  "/inbox",
  "/inbox?tab=sent",
  "/rituals",
  "/notifications",
  "/u/demo",
  "/u/aanya",
  "/settings/connections",
  "/settings/privacy",
  "/settings/notifications",
  "/settings/account",
  "/onboarding/profile",
  "/onboarding/sources",
  "/onboarding/privacy",
  "/onboarding/friends",
  "/connect/companion",
];

async function settle(page: Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
}

for (const theme of ["dark", "light"] as const) {
  test(`a11y public routes (${theme})`, async ({ page }) => {
    test.setTimeout(180_000);
    await page.emulateMedia({ colorScheme: theme });
    await page.addInitScript((t) => localStorage.setItem("jingle-theme", t), theme);
    for (const path of PUBLIC) {
      await settle(page, path);
      await expectNoA11yViolations(page);
    }
  });

  test(`a11y signed-in routes (${theme})`, async ({ page }) => {
    test.setTimeout(300_000);
    await page.addInitScript((t) => localStorage.setItem("jingle-theme", t), theme);
    await signIn(page);
    for (const path of SIGNED_IN) {
      await settle(page, path);
      await expectNoA11yViolations(page);
    }
    // Detail pages reached from lists.
    await settle(page, "/circles");
    await page.getByRole("link", { name: /KJ Somaiya crew/ }).click();
    await page.waitForLoadState("networkidle");
    await expectNoA11yViolations(page);
    await settle(page, "/blends");
    await page.getByRole("link", { name: /Demo \+ Aanya \+ Kabir/ }).click();
    await page.waitForLoadState("networkidle");
    await expectNoA11yViolations(page);
  });
}

test("keyboard: skip link first, lands on main, focus visible", async ({ page }) => {
  await signIn(page);
  await settle(page, "/home");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to content" });
  await expect(skip).toBeFocused();
  await expect(skip).toBeVisible(); // visible when focused (2.4.7)
  await page.keyboard.press("Enter");
  await expect(page.locator("main#main")).toBeFocused();
  // Tab onwards reaches real controls with a visible focus indicator.
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press("Tab");
    const outline = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return "none";
      const s = getComputedStyle(el);
      return `${s.outlineStyle}|${s.boxShadow}`;
    });
    expect(outline).not.toBe("none|none");
  }
});

test("staff console is accessible to moderators", async ({ page }) => {
  await signIn(page, "mod@jingle.local");
  for (const tab of ["Reports", "Appeals", "Audit log", "Flags", "Budgets", "Spotify testers"]) {
    await settle(page, "/staff");
    await page.getByRole("tab", { name: tab }).click();
    await page.waitForLoadState("networkidle");
    await expectNoA11yViolations(page);
  }
});
