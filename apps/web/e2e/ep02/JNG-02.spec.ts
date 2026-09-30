import { expect, test } from "@playwright/test";
import { expectNoA11yViolations, signIn } from "../helpers";

test.describe("EP-02 social graph", () => {
  test("JNG-02-02 accept a request, then JNG-02-03 remove the friend", async ({ page, request }) => {
    // A fresh person asks the demo account to be friends (self-contained; no reliance on seed state).
    const id = Date.now().toString(36);
    const username = `req_${id}`.slice(0, 20);
    const reg = await request.post("/api/v1/auth/register", {
      data: { email: `${username}@jingle.local`, password: "e2e-password-123", username, display_name: "Requester", birth_year: 1998 },
    });
    expect(reg.ok()).toBeTruthy();
    const { access } = (await reg.json()) as { access: string };
    const sent = await request.post("/api/v1/friends/requests", {
      data: { username: "demo" },
      headers: { Authorization: `Bearer ${access}` },
    });
    expect(sent.status()).toBe(201);

    await signIn(page);
    await page.goto("/friends?tab=requests");
    const incoming = page.getByRole("listitem").filter({ hasText: `@${username}` });
    await expect(incoming).toBeVisible();
    await expectNoA11yViolations(page);
    await incoming.getByRole("button", { name: "Accept" }).click();
    await expect(incoming).toHaveCount(0);

    await page.goto("/friends?tab=friends");
    const row = page.getByRole("listitem").filter({ hasText: `@${username}` });
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "More options for Requester" }).click();
    await page.getByRole("button", { name: "Remove friend" }).click();
    await page.getByRole("dialog", { name: "Remove Requester?" }).getByRole("button", { name: "Remove" }).click();
    await expect(page.getByRole("listitem").filter({ hasText: `@${username}` })).toHaveCount(0);
  });

  test("JNG-02-01 search finds people with the right button; JNG-02-07 invite link and QR", async ({ page }) => {
    await signIn(page);
    await page.goto("/friends?tab=find");
    await page.getByLabel("Search by username or name").fill("zoy");
    await expect(page.getByRole("listitem").filter({ hasText: "@zoya" }).getByText("Friends")).toBeVisible();
    await expect(page.getByRole("img", { name: "QR code for your invite link" })).toBeVisible();
    await expect(page.getByText(/\/invite\//)).toBeVisible();
    await expectNoA11yViolations(page);
  });

  test("JNG-02-05/06 privacy settings save and Private mode shows its banner", async ({ page }) => {
    await signIn(page);
    await page.goto("/settings/privacy");
    const off = page.getByRole("button", { name: "Turn off Private mode" });
    await expect(off.or(page.getByRole("button", { name: "Hide for 1 hour" }))).toBeVisible();
    if (await off.isVisible()) await off.click(); // left on by an interrupted run
    await page.getByRole("button", { name: "Hide for 1 hour" }).click();
    await expect(page.getByText(/Private mode is on/)).toBeVisible();
    await expectNoA11yViolations(page);
    await page.getByRole("button", { name: "Turn off Private mode" }).click();
    await expect(page.getByText(/Private mode is on/)).toHaveCount(0);
  });
});
