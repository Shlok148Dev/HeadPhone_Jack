import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Connector } from "../src/connectors/common";
import { createObserver } from "../src/content/observer";
import type { TrackState } from "../src/shared/types";

let state: TrackState | null;
const connector: Connector = { platform: "SPOTIFY", hosts: ["open.spotify.com"], read: () => state };
const base: TrackState = { platform: "SPOTIFY", artist: "A", title: "T", durationMs: 200_000, positionMs: 0, isPlaying: true };

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

function start() {
  const send = vi.fn();
  const target = new EventTarget();
  const obs = createObserver({ connector, env: () => ({}) as never, send, now: () => Date.now(), target });
  obs.start();
  return { send, obs, target };
}

describe("content observer", () => {
  it("sends on start, then only on change (deduped)", () => {
    state = { ...base };
    const { send } = start();
    expect(send).toHaveBeenCalledTimes(1);
    for (let i = 1; i <= 5; i++) {
      state = { ...base, positionMs: i * 2000 };
      vi.advanceTimersByTime(2000);
    }
    expect(send).toHaveBeenCalledTimes(1);
    state = { ...base, positionMs: 12_000, isPlaying: false };
    vi.advanceTimersByTime(2000);
    expect(send).toHaveBeenCalledTimes(2);
    expect(send).toHaveBeenLastCalledWith(expect.objectContaining({ isPlaying: false }));
  });

  it("sends on a seek and on a track change", () => {
    state = { ...base };
    const { send } = start();
    state = { ...base, positionMs: 100_000 };
    vi.advanceTimersByTime(2000);
    expect(send).toHaveBeenCalledTimes(2);
    state = { ...base, title: "Other", positionMs: 0 };
    vi.advanceTimersByTime(2000);
    expect(send).toHaveBeenCalledTimes(3);
  });

  it("keepalive every 15 s while playing, none while paused", () => {
    state = { ...base };
    const { send } = start();
    let pos = 0;
    for (let i = 0; i < 15; i++) {
      pos += 2000;
      state = { ...base, positionMs: pos };
      vi.advanceTimersByTime(2000);
    }
    expect(send.mock.calls.length).toBe(2); // start + keepalive at 16 s (polls are 2 s apart)
    state = { ...base, positionMs: pos, isPlaying: false };
    vi.advanceTimersByTime(2000);
    const n = send.mock.calls.length;
    vi.advanceTimersByTime(60_000);
    expect(send.mock.calls.length).toBe(n);
  });

  it("reacts to media element events quickly", () => {
    state = { ...base };
    const { send, target } = start();
    state = { ...base, isPlaying: false };
    target.dispatchEvent(new Event("pause"));
    vi.advanceTimersByTime(300);
    expect(send).toHaveBeenCalledTimes(2);
  });

  it("sends null on stop and survives a throwing connector", () => {
    state = { ...base };
    const { send, obs } = start();
    obs.stop();
    expect(send).toHaveBeenLastCalledWith(null);
    const bad = createObserver({ connector: { ...connector, read: () => { throw new Error("x"); } }, env: () => ({}) as never, send: vi.fn(), target: new EventTarget() });
    expect(() => bad.check()).not.toThrow();
  });
});
