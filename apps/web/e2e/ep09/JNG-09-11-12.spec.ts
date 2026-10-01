import { expect, test, type APIRequestContext } from "@playwright/test";
import { DEMO, expectNoA11yViolations, signIn } from "../helpers";

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

test.describe("EP-09 rituals", () => {
  test("JNG-09-01 battle card for each circle; JNG-09-05/06 recap flips and shares", async ({ page, browser }) => {
    await signIn(page);
    await page.goto("/rituals");
    const card = page.getByRole("article", { name: "KJ Somaiya crew" });
    await expect(card).toBeVisible();
    await expect(card.getByText(/Nominate until|Vote until|Results are in|Nominations open|Skipped/)).toBeVisible();
    if (await card.getByLabel(/Nominate a song|Change your pick/).isVisible()) {
      await card.getByLabel(/Nominate a song|Change your pick/).fill("Kasoor");
      await card.getByRole("list", { name: "Search results" }).getByRole("button", { name: "Nominate" }).first().click();
      await expect(card.getByText(/Your pick:/)).toBeVisible();
    }
    await card.getByRole("button", { name: "Season table" }).click();
    await expect(card.getByText(/of 8 weeks played/)).toBeVisible();
    await expectNoA11yViolations(page);

    const recap = page.getByRole("button", { name: /^Recap for .*Show details$/ });
    await expect(recap).toBeVisible();
    await recap.click();
    await expect(page.getByRole("button", { name: /details\. Show the front$/ })).toBeVisible();
    const stop = page.getByRole("button", { name: "Stop sharing" });
    if (await stop.isVisible()) await stop.click(); // left on by an interrupted run
    await page.getByRole("button", { name: "Share a link" }).click();
    const link = await page.getByLabel("Recap link").inputValue();
    const pub = await browser.newContext();
    const p = await pub.newPage();
    await p.goto(new URL(link).pathname);
    await expect(p.getByRole("heading", { name: /’s \w+ \d{4}$/ })).toBeVisible();
    await page.getByRole("button", { name: "Stop sharing" }).click();
    await p.reload();
    await expect(p.getByRole("heading", { name: /isn.t shared any more/ })).toBeVisible();
    await pub.close();
  });
});

test.describe("EP-11 notifications", () => {
  test("JNG-11-01 bell shows unread; centre lists it and marks read; JNG-11-03 settings save", async ({ page, request }) => {
    const a = await register(request, "na", "Nia Sender");
    const b = await register(request, "nb", "Noor Receiver");
    expect((await request.post("/api/v1/friends/requests", { data: { username: b.username }, headers: auth(a.access) })).status()).toBe(201);

    await signIn(page, b.email, PASSWORD);
    await page.goto("/home");
    await expect(page.getByRole("link", { name: "Notifications, 1 unread" })).toBeVisible();
    await page.getByRole("link", { name: "Notifications, 1 unread" }).click();
    await expect(page.getByRole("link", { name: /Nia Sender wants to be friends/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "Notifications", exact: true })).toBeVisible();
    await expectNoA11yViolations(page);

    await page.goto("/settings/notifications");
    await page.getByLabel("Battles push").uncheck();
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Saved")).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("Battles push")).not.toBeChecked();
    await expect(page.getByRole("button", { name: /Allow push notifications|Turn off push/ }).or(page.getByText(/isn.t set up/))).toBeVisible();
    await expectNoA11yViolations(page);
  });
});

test.describe("EP-12 trust", () => {
  test("JNG-12-02/03 moderator warns from the queue; audit records it; JNG-12-08 member appeals", async ({ page, browser, request }) => {
    const reporter = await register(request, "rp", "Rae Reporter");
    const target = await register(request, "tg", "Tao Target");
    const rep = await request.post("/api/v1/reports", {
      data: { target_type: "user", target_id: target.id, reason: "spam", details: `e2e ${target.username}` },
      headers: auth(reporter.access),
    });
    expect(rep.status()).toBe(201);

    await signIn(page, "mod@jingle.local", DEMO.password);
    await page.goto("/staff");
    await expect(page.getByRole("heading", { name: "Staff console" })).toBeVisible();
    const row = page.getByRole("listitem").filter({ hasText: `e2e ${target.username}` });
    await expect(row).toBeVisible();
    await expectNoA11yViolations(page);
    await row.getByLabel("Reason (the person sees it)").fill("Please stop spamming links");
    await row.getByRole("button", { name: "Warn" }).click();
    await expect(page.getByText("Action recorded")).toBeVisible();
    await page.getByRole("tab", { name: "Audit log" }).click();
    await expect(page.getByRole("table", { name: "Audit log" })).toContainText(`user:${target.id}`);

    const ctx = await browser.newContext();
    const t = await ctx.newPage();
    await signIn(t, target.email, PASSWORD);
    await t.goto("/settings/account");
    await expect(t.getByText("Reason: Please stop spamming links")).toBeVisible();
    await t.getByLabel("Why should we look again?").fill("I only shared one link");
    await t.getByRole("button", { name: "Appeal" }).click();
    await expect(t.getByText("Appeal: under review")).toBeVisible();
    await ctx.close();
  });
});
