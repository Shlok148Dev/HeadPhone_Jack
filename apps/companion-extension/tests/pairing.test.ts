import { describe, expect, it, vi } from "vitest";
import { installPairingListener, isPlausibleToken, MSG } from "../src/content/pairing-listener";
import type { PairResult } from "../src/shared/types";

const ORIGIN = "http://127.0.0.1:8080";
const TOKEN = "jgl_abcdefghijklmnop";

function fakeWindow() {
  const target = new EventTarget();
  const win = {
    location: { origin: ORIGIN },
    addEventListener: target.addEventListener.bind(target),
    removeEventListener: target.removeEventListener.bind(target),
    postMessage: vi.fn(),
  };
  const dispatch = (data: unknown, opts: { origin?: string; source?: unknown } = {}) =>
    target.dispatchEvent(
      Object.assign(new Event("message"), { data, origin: opts.origin ?? ORIGIN, source: "source" in opts ? opts.source : win }),
    );
  return { win, dispatch };
}

function setup(result: PairResult = { ok: true, userName: "aanya" }) {
  const { win, dispatch } = fakeWindow();
  const pair = vi.fn(async (_t: string) => result);
  installPairingListener({ win: win as unknown as Window, pair, version: "0.1.0" });
  return { win, dispatch, pair };
}

const flush = () => new Promise((r) => setTimeout(r, 0));

describe("pairing content script", () => {
  it("announces READY to the page's own origin on install", () => {
    const { win } = setup();
    expect(win.postMessage).toHaveBeenCalledWith({ type: MSG.ready, version: "0.1.0" }, ORIGIN);
  });

  it("accepts a same-origin, same-window token message and reports the result", async () => {
    const { win, dispatch, pair } = setup();
    dispatch({ type: MSG.token, token: TOKEN });
    await flush();
    expect(pair).toHaveBeenCalledWith(TOKEN);
    expect(win.postMessage).toHaveBeenLastCalledWith({ type: MSG.paired, ok: true, userName: "aanya" }, ORIGIN);
  });

  it("rejects cross-origin messages", async () => {
    const { dispatch, pair } = setup();
    dispatch({ type: MSG.token, token: TOKEN }, { origin: "https://evil.example" });
    await flush();
    expect(pair).not.toHaveBeenCalled();
  });

  it("rejects messages from another window (e.g. an iframe)", async () => {
    const { dispatch, pair } = setup();
    dispatch({ type: MSG.token, token: TOKEN }, { source: {} });
    dispatch({ type: MSG.token, token: TOKEN }, { source: null });
    await flush();
    expect(pair).not.toHaveBeenCalled();
  });

  it("ignores the wrong type or shape", async () => {
    const { dispatch, pair } = setup();
    dispatch({ type: "jingle_companion_token", token: TOKEN });
    dispatch({ type: "JINGLE_COMPANION_TOKEN_X", token: TOKEN });
    dispatch("JINGLE_COMPANION_TOKEN");
    dispatch(null);
    await flush();
    expect(pair).not.toHaveBeenCalled();
  });

  it("refuses implausible tokens without contacting the worker", async () => {
    const { win, dispatch, pair } = setup();
    dispatch({ type: MSG.token, token: "short" });
    dispatch({ type: MSG.token, token: { toString: () => TOKEN } });
    await flush();
    expect(pair).not.toHaveBeenCalled();
    expect(win.postMessage).toHaveBeenLastCalledWith({ type: MSG.paired, ok: false, error: "invalid_token" }, ORIGIN);
  });

  it("answers PING with READY", () => {
    const { win, dispatch } = setup();
    win.postMessage.mockClear();
    dispatch({ type: MSG.ping });
    expect(win.postMessage).toHaveBeenCalledWith({ type: MSG.ready, version: "0.1.0" }, ORIGIN);
  });

  it("token plausibility", () => {
    expect(isPlausibleToken(TOKEN)).toBe(true);
    expect(isPlausibleToken("has space inside")).toBe(false);
    expect(isPlausibleToken("x".repeat(600))).toBe(false);
  });
});

describe("zero-setup pairing (D-EXT-02)", () => {
  it("READY tells the page whether this extension is already connected", async () => {
    const { win, dispatch } = fakeWindow();
    const status = vi.fn(async () => ({ paired: false }));
    installPairingListener({ win: win as unknown as Window, pair: vi.fn(), version: "0.1.0", status });
    await flush();
    expect(win.postMessage).toHaveBeenCalledWith({ type: MSG.ready, version: "0.1.0", paired: false }, ORIGIN);
    status.mockResolvedValueOnce({ paired: true });
    dispatch({ type: MSG.ping });
    await flush();
    expect(win.postMessage).toHaveBeenLastCalledWith({ type: MSG.ready, version: "0.1.0", paired: true }, ORIGIN);
  });

  it("still answers READY if the status check fails", async () => {
    const { win } = fakeWindow();
    installPairingListener({ win: win as unknown as Window, pair: vi.fn(), version: "0.1.0", status: async () => Promise.reject(new Error("x")) });
    await flush();
    expect(win.postMessage).toHaveBeenCalledWith({ type: MSG.ready, version: "0.1.0" }, ORIGIN);
  });
});
