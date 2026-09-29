import { defineConfig, devices } from "@playwright/test";

/** E2E runs against the Compose stack in demo mode (docker compose up), via the edge. */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:8080",
    ...devices["Desktop Chrome"],
  },
});
