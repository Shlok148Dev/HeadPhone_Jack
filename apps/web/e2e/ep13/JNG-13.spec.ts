import { expect, test } from "@playwright/test";
import { expectNoA11yViolations, signIn } from "../helpers";

test("JNG-13-04 download my data; JNG-01-10 delete my account", async ({ page, request }) => {
  const username = `dr_${Date.now().toString(36)}`.slice(0, 20);
  const email = `${username}@jingle.local`;
  const password = "e2e-password-123";
  const reg = await request.post("/api/v1/auth/register", {
    data: { email, password, username, display_name: "Dana Rights", birth_year: 1998 },
  });
  expect(reg.ok()).toBeTruthy();

  await signIn(page, email, password);
  await page.goto("/settings/account");
  await expect(page.getByRole("heading", { name: "Your data" })).toBeVisible();
  await expectNoA11yViolations(page);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download my data" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("jingle-export.json");
  const body = JSON.parse(await (await file.createReadStream()).toArray().then((c) => Buffer.concat(c).toString()));
  expect(body.profile.username).toBe(username);
  for (const key of ["friends", "circles", "sends", "received", "listens", "recaps", "notifications"]) expect(body).toHaveProperty(key);

  await page.getByRole("button", { name: "Delete my account" }).click();
  const dialog = page.getByRole("dialog", { name: "Delete your account?" });
  await dialog.getByLabel(/Your password/).fill("wrong-password-1");
  await dialog.getByRole("button", { name: "Delete my account" }).click();
  await expect(dialog.getByRole("alert")).toContainText("incorrect");
  await dialog.getByLabel(/Your password/).fill(password);
  await dialog.getByRole("button", { name: "Delete my account" }).click();
  await page.waitForURL((u) => u.pathname === "/");
  const again = await request.post("/api/v1/auth/login", { data: { email, password } });
  expect(again.ok()).toBeFalsy();
});
