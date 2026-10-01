import { expect, test, type APIRequestContext } from "@playwright/test";
import { expectNoA11yViolations, signIn } from "../helpers";

const PASSWORD = "e2e-password-123";

async function register(request: APIRequestContext, prefix: string, name: string) {
  const username = `${prefix}_${Date.now().toString(36)}${Math.floor(Math.random() * 1e4)}`.slice(0, 20);
  const res = await request.post("/api/v1/auth/register", {
    data: { email: `${username}@jingle.local`, password: PASSWORD, username, display_name: name, birth_year: 1998 },
  });
  expect(res.ok()).toBeTruthy();
  const body = (await res.json()) as { access: string; user: { id: string } };
  return { username, email: `${username}@jingle.local`, access: body.access, id: body.user.id };
}

const auth = (access: string) => ({ Authorization: `Bearer ${access}` });

async function befriend(request: APIRequestContext, a: { access: string }, b: { username: string; access: string }) {
  const sent = await request.post("/api/v1/friends/requests", { data: { username: b.username }, headers: auth(a.access) });
  expect(sent.status()).toBe(201);
  const list = (await (await request.get("/api/v1/friends/requests", { headers: auth(b.access) })).json()) as {
    id: string;
    direction: string;
  }[];
  const incoming = list.find((r) => r.direction === "incoming")!;
  expect((await request.post(`/api/v1/friends/requests/${incoming.id}/accept`, { headers: auth(b.access) })).ok()).toBeTruthy();
}

test.describe("EP-07 Blends and live sessions", () => {
  test("JNG-07-01/02 make a Blend with reasons; JNG-07-03 pin survives regenerate", async ({ page }) => {
    await signIn(page);
    await page.goto("/blends");
    await expect(page.getByRole("heading", { name: "Blends", level: 1 })).toBeVisible();
    await page.getByRole("button", { name: "New Blend" }).click();
    const dialog = page.getByRole("dialog", { name: "New Blend" });
    await dialog.getByLabel("Who's in?").fill("aany");
    await dialog.getByRole("button", { name: "Aanya", exact: true }).click();
    await dialog.getByRole("button", { name: "Make Blend" }).click();
    await page.waitForURL(/\/blends\/[0-9a-f-]+$/);
    const songs = page.getByRole("list", { name: "Songs" }).getByRole("listitem");
    await expect(songs.first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Saving to your music app isn.t available yet/)).toBeVisible(); // JNG-07-04
    await expectNoA11yViolations(page);

    const first = songs.first();
    const title = (await first.locator("p").first().textContent())!.trim();
    await first.getByRole("button", { name: `Pin ${title}` }).click();
    await expect(first.getByRole("button", { name: `Unpin ${title}` })).toBeVisible();
    await page.getByRole("button", { name: "Regenerate" }).click();
    await expect(page.getByText("Fresh Blend ready")).toBeVisible();
    await expect(songs.first().getByRole("button", { name: `Unpin ${title}` })).toBeVisible();
    await expect(songs.first()).toContainText("Pinned by");
    await page.getByRole("button", { name: "Leave Blend" }).click(); // keep the demo account tidy
    await page.waitForURL(/\/blends$/);
  });

  test("JNG-07-05…09 live room: join, add, vote live, host hand-over", async ({ page, browser, request }) => {
    const host = await register(request, "host", "Hana Host");
    const guest = await register(request, "gst", "Gita Guest");
    await befriend(request, guest, host);

    await signIn(page, host.email, PASSWORD);
    await page.goto("/blends");
    await page.getByRole("button", { name: "Listen together" }).click();
    const dialog = page.getByRole("dialog", { name: "Listen together" });
    await dialog.getByRole("button", { name: "Gita Guest", exact: true }).click();
    await dialog.getByRole("button", { name: "Start session" }).click();
    await page.waitForURL(/\/sessions\/[0-9a-f-]+$/);
    const url = new URL(page.url()).pathname;
    await expect(page.getByText("Hosted by you")).toBeVisible();

    const ctx = await browser.newContext();
    const g = await ctx.newPage();
    await signIn(g, guest.email, PASSWORD);
    await g.goto(url);
    await g.getByRole("button", { name: "Join session" }).click({ timeout: 20_000 });
    await expect(g.getByRole("heading", { name: "Up next" })).toBeVisible();

    // Host adds a song: the guest sees it without refreshing (queue:delta over the socket).
    await page.getByLabel("Find a song").fill("Kesariya");
    await page.getByRole("list", { name: "Search results" }).getByRole("button", { name: "Add" }).first().click();
    const guestQueue = g.getByRole("list", { name: "Queue" });
    await expect(guestQueue.getByText("Kesariya")).toBeVisible({ timeout: 10_000 });
    await expect(guestQueue).toContainText("added by Hana Host");

    // Guest adds one anonymously and votes the host's song up; the host sees the new order live.
    await g.getByLabel("Find a song").fill("Excuses");
    await g.getByLabel("Add anonymously").check();
    await g.getByRole("list", { name: "Search results" }).getByRole("button", { name: "Add" }).first().click();
    await expect(page.getByRole("list", { name: "Queue" })).toContainText("added anonymously", { timeout: 10_000 });
    const up = g.getByRole("button", { name: /^Vote up Excuses/ });
    await up.click();
    await expect(up).toHaveAttribute("aria-pressed", "true");
    await up.click(); // toggles off: one vote each
    await expect(up).toHaveAttribute("aria-pressed", "false");
    await up.click();
    await expect(up).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("list", { name: "Queue" }).getByRole("listitem").first()).toContainText("Excuses", { timeout: 10_000 });
    await expectNoA11yViolations(g);

    // JNG-07-08: the host leaves; the guest becomes host.
    await page.getByRole("button", { name: "Leave" }).click();
    await expect(g.getByText("Hosted by you")).toBeVisible({ timeout: 10_000 });
    await expect(g.getByRole("button", { name: "Play next" })).toBeVisible();
    await g.getByRole("button", { name: "Play next" }).click();
    await expect(g.getByRole("region").or(g.locator("section")).filter({ hasText: "Now" }).first()).toContainText("Excuses");
    await ctx.close();
  });

  test("Gherkin Concurrent votes: 10 parallel votes all count (PostgreSQL)", async ({ request }) => {
    const host = await register(request, "hv", "Vote Host");
    const voters = [];
    for (let i = 0; i < 10; i++) voters.push(await register(request, `v${i}`, `Voter ${i}`));
    for (const v of voters) await befriend(request, v, host);
    const start = await request.post("/api/v1/sessions", {
      data: { user_ids: voters.map((v) => v.id) },
      headers: auth(host.access),
    });
    expect(start.status()).toBe(201);
    const { id } = (await start.json()) as { id: string };
    for (const v of voters) expect((await request.post(`/api/v1/sessions/${id}/join`, { headers: auth(v.access) })).ok()).toBeTruthy();
    const entry = await request.post(`/api/v1/sessions/${id}/queue`, {
      data: { title: "Kesariya", artist: "Arijit Singh", idempotency_key: "k1" },
      headers: auth(host.access),
    });
    const { id: entryId } = (await entry.json()) as { id: string };
    const results = await Promise.all(
      voters.map((v) => request.post(`/api/v1/queue/${entryId}/vote`, { data: { value: 1 }, headers: auth(v.access) })),
    );
    expect(results.every((r) => r.ok())).toBeTruthy();
    const state = (await (await request.get(`/api/v1/sessions/${id}`, { headers: auth(host.access) })).json()) as {
      queue: { score: number }[];
    };
    expect(state.queue[0]!.score).toBe(10);
  });
});
