import { expect, test, type APIRequestContext } from "@playwright/test";
import { ROUTE_WORDS, expectNoA11yViolations } from "../helpers";

async function register(request: APIRequestContext, username: string) {
  const r = await request.post("/api/v1/auth/register", {
    data: { email: `${username}@jingle.local`, password: "e2e-password-123", username, display_name: username, birth_year: 1998 },
  });
  expect(r.ok()).toBeTruthy();
  return ((await r.json()) as { access: string }).access;
}

test("JNG-05-02 a friend's Live card appears without refreshing", async ({ page, request }) => {
  test.setTimeout(90_000);
  const id = Date.now().toString(36);
  const [a, b] = [`viewer_${id}`.slice(0, 20), `player_${id}`.slice(0, 20)];
  const tokA = await register(request, a);
  const tokB = await register(request, b);
  const auth = (t: string) => ({ Authorization: `Bearer ${t}` });

  // Become friends, and give B a push token (with consent) like the Companion would.
  const req = await request.post("/api/v1/friends/requests", { data: { username: b }, headers: auth(tokA) });
  expect(req.status()).toBe(201);
  const reqs = (await (await request.get("/api/v1/friends/requests", { headers: auth(tokB) })).json()) as { id: string }[];
  expect((await request.post(`/api/v1/friends/requests/${reqs[0]!.id}/accept`, { headers: auth(tokB) })).ok()).toBeTruthy();
  await request.post("/api/v1/me/consents/activity_sharing", { data: { given: true }, headers: auth(tokB) });
  const push = ((await (await request.post("/api/v1/sources/companion/token", { headers: auth(tokB) })).json()) as { token: string }).token;

  // A opens Home: B has no plays yet.
  await page.goto("/signin");
  await page.getByLabel("Email").fill(`${a}@jingle.local`);
  await page.getByLabel("Password", { exact: true }).fill("e2e-password-123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/home/);
  await expect(page.getByText(/No(body| one).s playing right now/)).toBeVisible();

  // B starts playing on YouTube Music in the browser; A's page updates live.
  const sent = await request.post("/ingest/1/submit-listens", {
    headers: { Authorization: `Token ${push}` },
    data: { listen_type: "playing_now", payload: [{ track_metadata: { artist_name: "Anuv Jain", track_name: "Husn", additional_info: { music_service: "music.youtube.com" } } }] },
  });
  expect(sent.ok()).toBeTruthy();
  // Home shows friends' listening in the Now stage (D-HOME-02).
  const stage = page.getByRole("region", { name: "Playing now" });
  await expect(stage.getByText("Live on YouTube Music").first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Husn").first()).toBeVisible();
  await expect(page.locator("main")).not.toContainText(ROUTE_WORDS);
  await expectNoA11yViolations(page);
});
