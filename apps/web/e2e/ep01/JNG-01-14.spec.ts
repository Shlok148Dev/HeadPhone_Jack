import { expect, test, type Page } from "@playwright/test";
import { ROUTE_WORDS, expectNoA11yViolations } from "../helpers";

/**
 * One-tap Connect (D-CONNECT-01, D-EXT-02). The installed extension is simulated with the same
 * window.postMessage protocol its pairing script speaks (the extension side is unit-tested): it
 * answers PING with READY, takes the token, confirms PAIRED and, like the real one, submits a play.
 */
async function fakeExtension(page: Page, installed: boolean) {
  await page.addInitScript((on: boolean) => {
    if (!on) return;
    let paired = false;
    const reply = (m: object) => window.postMessage(m, location.origin);
    window.addEventListener("message", async (e) => {
      if (e.source !== window) return;
      if (e.data?.type === "JINGLE_COMPANION_PING")
        reply({ type: "JINGLE_COMPANION_READY", version: "test", paired });
      if (e.data?.type === "JINGLE_COMPANION_TOKEN") {
        paired = true;
        reply({ type: "JINGLE_COMPANION_PAIRED", ok: true });
        await fetch("/ingest/1/submit-listens", {
          method: "POST",
          headers: {
            Authorization: `Token ${e.data.token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            listen_type: "single",
            payload: [
              {
                listened_at: Math.floor(Date.now() / 1000) - 30,
                track_metadata: {
                  artist_name: "Arijit Singh",
                  track_name: "Tum Hi Ho",
                  additional_info: {
                    music_service: "music.youtube.com",
                    submission_client: "Jingle Companion",
                    submission_client_version: "test",
                  },
                },
              },
            ],
          }),
        });
      }
    });
  }, installed);
}

async function signUp(page: Page, tag: string) {
  const id = `${tag}${Date.now().toString(36)}`;
  await page.goto("/signup");
  await page.getByLabel("Email").fill(`${id}@jingle.local`);
  await page.getByLabel("Password", { exact: true }).fill("e2e-password-123");
  await page.getByLabel("Username").fill(id.slice(0, 20));
  await page.getByLabel("Birth year").selectOption("1999");
  await page.getByLabel(/I agree/).check();
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL(/\/onboarding\/sources/);
}

test.describe("JNG-01-14 one tap per music app (+ JNG-01-09 unlink)", () => {
  test("YouTube Music with Jingle in Chrome: one tap, connected, then disconnect", async ({
    page,
  }) => {
    test.setTimeout(90_000);
    await fakeExtension(page, true);
    await signUp(page, "yt");
    await expect(
      page.getByRole("heading", { name: "Connect your music" }),
    ).toBeVisible();
    await expect(page.locator("main")).not.toContainText(ROUTE_WORDS); // BR-14: no plumbing words
    await expectNoA11yViolations(page);

    await page.getByRole("button", { name: /YouTube Music/ }).click();
    const tile = page.getByRole("button", { name: /YouTube Music/ });
    await expect(tile).toContainText(/Connected|Play a song to finish/, {
      timeout: 30_000,
    });
    await expect(page.getByRole("button", { name: "Continue" })).toBeEnabled();

    await page.goto("/settings/connections");
    const row = page
      .getByRole("list", { name: "Connected apps" })
      .getByRole("listitem")
      .filter({ hasText: "YouTube Music" });
    await row.getByRole("button", { name: "Disconnect" }).click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Disconnect" })
      .click();
    await expect(
      page
        .getByRole("list", { name: "Connected apps" })
        .getByText("YouTube Music"),
    ).toHaveCount(0, { timeout: 15_000 });
  });

  test("Amazon Music without the extension: a single Add to Chrome prompt, never an error", async ({
    page,
  }) => {
    await fakeExtension(page, false);
    await signUp(page, "am");
    await page.getByRole("button", { name: /Amazon Music/ }).click();
    await expect(
      page.getByText("Add Jingle to Chrome to connect Amazon Music"),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  });

  test("Spotify without Jingle's keys says so plainly, never an extension detour (D-CONNECT-02)", async ({
    page,
  }) => {
    await signUp(page, "sp");
    await page.getByRole("button", { name: /Spotify/ }).click();
    // With keys: Spotify's or Last.fm's own login opens. Without (CI): an honest one-liner.
    await expect
      .poll(
        async () =>
          /spotify\.com|last\.fm/.test(page.url()) ||
          (await page
            .getByText(/Spotify sign-in isn.t switched on for Jingle yet/)
            .count()) > 0,
        { timeout: 20_000 },
      )
      .toBe(true);
    await expect(page.getByText(/Add Jingle to Chrome/)).toHaveCount(0);
    await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  });

  test("Phones: honest one-liners instead of an extension", async ({
    browser,
  }) => {
    const ctx = await browser.newContext({
      userAgent:
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
      viewport: { width: 390, height: 844 },
    });
    const page = await ctx.newPage();
    await signUp(page, "ph");
    await page.getByRole("button", { name: /YouTube Music/ }).click();
    await expect(
      page.getByText(
        /iPhones don.t let any app see what YouTube Music is playing/,
      ),
    ).toBeVisible({ timeout: 15_000 });
    await ctx.close();
  });

  test("Inside the Jingle Android app: tap, one toggle, and the first song connects it", async ({
    browser,
  }) => {
    const ctx = await browser.newContext({
      userAgent:
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36",
      viewport: { width: 412, height: 915 },
    });
    const page = await ctx.newPage();
    // The app's bridge (MainActivity.kt): takes the token; PlayListener then submits from the phone.
    await page.addInitScript(() => {
      (window as unknown as { JingleAndroid: object }).JingleAndroid = {
        addEventListener: () => undefined,
        postMessage: (raw: string) => {
          const m = JSON.parse(raw) as { type: string; token?: string };
          if (m.type !== "pair") return;
          void fetch("/ingest/1/submit-listens", {
            method: "POST",
            headers: {
              Authorization: `Token ${m.token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              listen_type: "single",
              payload: [
                {
                  listened_at: Math.floor(Date.now() / 1000) - 30,
                  track_metadata: {
                    artist_name: "AP Dhillon",
                    track_name: "With You",
                    additional_info: {
                      music_service: "music.amazon.com",
                      submission_client: "Jingle Android",
                      submission_client_version: "test",
                    },
                  },
                },
              ],
            }),
          });
        },
      };
    });
    await signUp(page, "an");
    await page.getByRole("button", { name: /Amazon Music/ }).click();
    await expect(
      page.getByRole("button", { name: /Amazon Music/ }),
    ).toContainText(/Play a song on Amazon Music to finish|Connected/, {
      timeout: 15_000,
    });
    await expect(
      page.getByRole("button", { name: /Amazon Music/ }),
    ).toContainText("Connected", { timeout: 30_000 });
    await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
    await ctx.close();
  });
});
