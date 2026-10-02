import { expect, test } from "@playwright/test";
import { signIn } from "../helpers";

/** EP-14 Daily Drop + Tune in on Home (JNG-14-01, D-HOME-01, D-TUNE-01). Read-only: the demo keeps its own drop. */
test.describe("EP-14 Home stage, Tune in and Daily Drop", () => {
  test("stage offers Tune in in your app; Drop is sealed until you drop", async ({ page }) => {
    await signIn(page);
    const stage = page.getByRole("region", { name: /Playing now|Just played/ });
    await expect(stage).toBeVisible();
    // Honest wording: "Play in X" for an exact link, "Find in X" for a search; never "Open in my app".
    await expect(stage.getByRole("link", { name: /^(Play|Find) in (Spotify|Apple Music|YouTube Music|Amazon Music): / })).toBeVisible();
    await expect(stage.getByRole("button", { name: "Send to a friend" })).toBeVisible();

    const drop = page.getByRole("region", { name: /One song\. Your pick for today\.|What everyone dropped today/ });
    await expect(drop).toBeVisible();
    if (await drop.getByText("One song. Your pick for today.").isVisible()) {
      // Sealed: who dropped may show, but no friend's song title is in the section.
      await expect(drop.getByRole("button", { name: "Drop it" })).toBeDisabled();
      await drop.getByLabel("Your song for today").fill("Kasoor");
      await expect(drop.getByRole("list", { name: "Songs" }).getByRole("button").first()).toBeVisible();
    }
  });
});
