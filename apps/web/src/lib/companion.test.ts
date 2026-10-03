import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({ api: vi.fn() }));
import { api } from "@/lib/api";
import {
  MSG,
  canRunExtension,
  detectExtension,
  isPhone,
  pairExtension,
} from "./companion";

/** Plays the extension's side of the window.postMessage protocol (D-EXT-02). */
function fakeExtension(opts: { paired?: boolean; pairOk?: boolean }) {
  const say = (data: object) =>
    window.dispatchEvent(
      new MessageEvent("message", {
        data,
        origin: window.location.origin,
        source: window,
      }),
    );
  const on = (e: MessageEvent) => {
    if (e.data?.type === MSG.ping)
      say({ type: MSG.ready, version: "1.2.0", paired: opts.paired ?? false });
    if (e.data?.type === MSG.token)
      say({ type: MSG.paired, ok: opts.pairOk ?? true });
  };
  const orig = window.postMessage.bind(window);
  vi.spyOn(window, "postMessage").mockImplementation(((m: unknown) =>
    on(new MessageEvent("message", { data: m }))) as typeof window.postMessage);
  return orig;
}
const ua = (s: string) =>
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue(s);

afterEach(() => vi.restoreAllMocks());

describe("lib/companion (D-EXT-02 zero-setup pairing, web half)", () => {
  it("detects an installed, not yet paired extension", async () => {
    fakeExtension({ paired: false });
    await expect(detectExtension(200)).resolves.toEqual({
      installed: true,
      paired: false,
      version: "1.2.0",
    });
  });

  it("reports no extension after the timeout", async () => {
    vi.spyOn(window, "postMessage").mockImplementation(() => undefined);
    await expect(detectExtension(20)).resolves.toEqual({ installed: false });
  });

  it("pairs: mints a token, hands it over, resolves on PAIRED", async () => {
    vi.mocked(api).mockResolvedValueOnce({ token: "t".repeat(40) });
    fakeExtension({ pairOk: true });
    await expect(pairExtension()).resolves.toEqual({ ok: true });
    expect(api).toHaveBeenCalledWith("/sources/companion/token", {
      method: "POST",
    });
  });

  it("surfaces CONSENT_REQUIRED so the page can ask once with Allow", async () => {
    vi.mocked(api).mockRejectedValueOnce(
      Object.assign(new Error("x"), { code: "CONSENT_REQUIRED" }),
    );
    await expect(pairExtension()).resolves.toEqual({
      ok: false,
      error: "CONSENT_REQUIRED",
    });
  });

  it("knows where an extension can run", () => {
    ua(
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36",
    );
    expect(canRunExtension()).toBe(true);
    ua(
      "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36",
    );
    expect(canRunExtension()).toBe(false);
    expect(isPhone()).toBe(true);
    ua(
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15",
    );
    expect(canRunExtension()).toBe(false);
  });
});
