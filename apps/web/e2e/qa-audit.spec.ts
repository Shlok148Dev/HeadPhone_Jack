import { test, type Page } from "@playwright/test";
import * as fs from "node:fs";
import { signIn } from "./helpers";

/**
 * Black-box product audit (QA campaign, run with QA_AUDIT=1). Visits every route at three widths in
 * both themes and records defects a user would notice. Writes artifacts/qa/audit.json; never asserts,
 * so one run reports everything at once.
 */
test.skip(process.env.QA_AUDIT !== "1", "only on request");

const PUBLIC = ["/", "/signin", "/signup", "/design"];
const APP = [
  "/home",
  "/friends",
  "/friends?tab=requests",
  "/friends?tab=suggestions",
  "/circles",
  "/blends",
  "/rituals",
  "/inbox",
  "/notifications",
  "/settings/connections",
  "/settings/privacy",
  "/settings/notifications",
  "/settings/account",
  "/u/aanya",
  "/u/demo",
  "/connect/companion",
  "/onboarding/profile",
  "/staff",
];
const SIZES = [
  { w: 1440, h: 900 },
  { w: 900, h: 760 },
  { w: 390, h: 844 },
];
const BAD_TEXT = /\b(undefined|NaN|null|\[object Object\]|lorem ipsum|TODO|FIXME)\b/i;

type Finding = { route: string; size: number; theme: string; kind: string; detail: string };

async function audit(page: Page, route: string, size: number, theme: string, out: Finding[], errors: string[]) {
  const t0 = Date.now();
  errors.length = 0;
  const failed: string[] = [];
  const onResp = (r: import("@playwright/test").Response) => {
    const u = r.url();
    if (r.status() >= 400 && !u.includes("/auth/refresh") && !u.includes("/auth/session")) failed.push(`${r.status()} ${u.replace(/^https?:\/\/[^/]+/, "").slice(0, 90)}`);
  };
  page.on("response", onResp);
  await page.goto(route);
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => out.push({ route, size, theme, kind: "never-idle", detail: "network never settled in 15 s" }));
  await page.waitForTimeout(1200);
  const ms = Date.now() - t0;
  page.off("response", onResp);
  const r = await page.evaluate(
    ({ badText }) => {
      const re = new RegExp(badText, "i");
      const vis = (el: Element) => {
        const b = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return b.width > 0 && b.height > 0 && s.visibility !== "hidden" && s.display !== "none";
      };
      const imgs = [...document.querySelectorAll("img")].filter(vis) as HTMLImageElement[];
      const broken = imgs.filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.currentSrc.slice(-50));
      const blurry = imgs
        .filter((i) => i.naturalWidth > 0 && i.naturalWidth < i.getBoundingClientRect().width * 0.95)
        .map((i) => `${Math.round(i.getBoundingClientRect().width)}css<-${i.naturalWidth}px`);
      const generative = document.querySelectorAll('[data-generative="true"], svg[data-cover="generative"]').length;
      const overflow = document.documentElement.scrollWidth - window.innerWidth;
      const small = [...document.querySelectorAll("a[href], button, input, select, textarea, [role=button], [role=link], [role=tab]")]
        .filter(vis)
        .filter((el) => {
          const b = el.getBoundingClientRect();
          // WCAG 2.2 target size (minimum) is 24×24; our own bar is 44×44 for primary controls.
          return b.width < 24 || b.height < 24;
        })
        .map((el) => `${el.tagName.toLowerCase()}:${(el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 30)}`);
      const text = document.body.innerText;
      const badMatch = text.match(re);
      const h1 = document.querySelectorAll("h1").length;
      const offscreenRight = [...document.querySelectorAll("main *")]
        .filter(vis)
        .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 2 && !el.closest("[class*='overflow-x-auto'],[class*='overflow-hidden'],[class*='snap-x']"))
        .slice(0, 3)
        .map((el) => `${el.tagName.toLowerCase()}.${String(el.className).slice(0, 40)}`);
      return { broken, blurry: blurry.slice(0, 4), blurryCount: blurry.length, generative, overflow, small: small.slice(0, 6), smallCount: small.length, bad: badMatch ? badMatch[0] : null, h1, offscreenRight, imgs: imgs.length };
    },
    { badText: BAD_TEXT.source },
  );
  const add = (kind: string, detail: string) => out.push({ route, size, theme, kind, detail });
  if (errors.length) add("console-error", errors.slice(0, 3).join(" || ").slice(0, 400));
  if (failed.length) add("http-error", failed.slice(0, 4).join(" | "));
  if (r.broken.length) add("broken-image", `${r.broken.length}: ${r.broken.slice(0, 2).join(", ")}`);
  if (r.blurryCount) add("blurry-image", `${r.blurryCount}: ${r.blurry.join(", ")}`);
  if (r.overflow > 1) add("horizontal-scroll", `${r.overflow}px wider than the viewport`);
  if (r.offscreenRight.length) add("offscreen-content", r.offscreenRight.join(", "));
  if (r.smallCount) add("tiny-target", `${r.smallCount}: ${r.small.join(" ; ")}`);
  if (r.bad) add("placeholder-text", `"${r.bad}" visible on page`);
  if (r.h1 !== 1) add("heading-structure", `${r.h1} h1 elements`);
  if (ms > 4000) add("slow-load", `${ms} ms to settle`);
  return { ms, imgs: r.imgs };
}

const OUT = "../../artifacts/qa/audit.jsonl";

for (const theme of ["dark", "light"] as const) {
  for (const { w, h } of SIZES) {
    test(`qa audit ${theme} ${w}`, async ({ page }) => {
      test.setTimeout(600_000);
      fs.mkdirSync("../../artifacts/qa", { recursive: true });
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
      page.on("console", (m) => {
        if (m.type() === "error" && !/401 \(Unauthorized\)/.test(m.text())) errors.push(m.text());
      });
      await page.addInitScript((t) => localStorage.setItem("jingle-theme", t), theme);
      await page.setViewportSize({ width: w, height: h });
      // Each page's findings are appended immediately, so a timeout never loses the run.
      const visit = async (route: string) => {
        const out: Finding[] = [];
        const r = await audit(page, route, w, theme, out, errors);
        fs.appendFileSync(OUT, JSON.stringify({ route, size: w, theme, ms: r.ms, imgs: r.imgs, findings: out }) + "\n");
      };
      for (const route of PUBLIC) await visit(route);
      await signIn(page);
      for (const route of APP) await visit(route);
      for (const [list, link] of [["/circles", /KJ Somaiya crew/], ["/blends", /Demo \+ Aanya \+ Kabir/]] as const) {
        await page.goto(list);
        const a = page.getByRole("link", { name: link }).first();
        if (await a.isVisible().catch(() => false)) {
          await a.click({ timeout: 10_000 }).catch(() => undefined);
          await page.waitForLoadState("networkidle").catch(() => undefined);
          await visit(new URL(page.url()).pathname);
        }
      }
    });
  }
}
