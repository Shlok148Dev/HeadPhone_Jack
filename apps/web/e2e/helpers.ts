import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export const DEMO = { email: "demo@jingle.local", password: process.env.DEMO_PASSWORD ?? "jingle-demo-2026" };

/** Route words must never appear in product UI outside Settings → Connections (ADR-0002). */
export const ROUTE_WORDS = /ListenBrainz|Last\.fm|scrobbl|\bvia\b|Companion|bridge/i;

export async function signIn(page: Page, email = DEMO.email, password = DEMO.password) {
  await page.goto("/signin");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/(home|onboarding)/);
}

export async function setTheme(page: Page, theme: "dark" | "light") {
  await page.addInitScript((t) => {
    try {
      localStorage.setItem("jingle-theme", t);
    } catch {
      /* ignore */
    }
  }, theme);
}

export async function expectNoA11yViolations(page: Page) {
  // Measure the settled UI: entry animations briefly fade text in, which axe reads as low contrast.
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.waitForTimeout(400);
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.html.slice(0, 160)).join(" | ")}`)).toEqual([]);
}

export async function snap(page: Page, name: string) {
  await page.screenshot({ path: `../../artifacts/screenshots/s1/${name}.png`, fullPage: true });
}
