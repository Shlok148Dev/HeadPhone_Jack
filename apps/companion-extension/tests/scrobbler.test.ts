import { describe, expect, it } from "vitest";
import { RULES, Scrobbler, type Emission } from "../src/background/scrobbler";
import type { TrackState } from "../src/shared/types";

const T0 = Date.UTC(2026, 8, 29, 10, 0, 0);

function setup() {
  let now = T0;
  const clock = { now: () => now, advance: (ms: number) => (now += ms) };
  return { clock, sc: new Scrobbler(clock.now) };
}

const track = (over: Partial<TrackState> = {}): TrackState => ({
  platform: "YOUTUBE_MUSIC",
  artist: "Artist",
  title: "Song",
  durationMs: 200_000,
  positionMs: 0,
  isPlaying: true,
  ...over,
});

const kinds = (e: Emission[]) => e.map((x) => x.kind);

/**
 * Simulate `seconds` of wall time: a worker tick every 5 s and, like the real content observer,
 * a keepalive report of `page` every 15 s (omit `page` to simulate a page that stopped reporting).
 */
function run(sc: Scrobbler, clock: { advance: (ms: number) => void }, seconds: number, page?: TrackState): Emission[] {
  const out: Emission[] = [];
  for (let s = 5; s <= seconds; s += 5) {
    clock.advance(5000);
    if (page && s % 15 === 0) {
      const { positionMs: _omit, ...keepalive } = page;
      out.push(...sc.update("1", keepalive));
    }
    out.push(...sc.tick());
  }
  return out;
}

describe("Scrobbler", () => {
  it("sends playing_now when a new track starts playing", () => {
    const { sc } = setup();
    expect(kinds(sc.update("1", track()))).toEqual(["playing_now"]);
  });

  it("does not send playing_now for a paused track", () => {
    const { sc } = setup();
    expect(sc.update("1", track({ isPlaying: false }))).toEqual([]);
  });

  it("heartbeats playing_now every 30 s while the page keeps reporting", () => {
    const { sc, clock } = setup();
    const tr = track({ durationMs: 600_000 });
    sc.update("1", tr);
    const out = run(sc, clock, 90, tr);
    expect(kinds(out).filter((k) => k === "playing_now")).toHaveLength(3);
  });

  it("BR-01: a page that goes silent stops heartbeats and never scrobbles falsely", () => {
    const { sc, clock } = setup();
    sc.update("1", track({ durationMs: 200_000 }));
    const out = run(sc, clock, 30 * 60); // 30 min, no content updates (crash/freeze/sleep)
    const heartbeats = out.filter((e) => e.kind === "playing_now");
    expect(heartbeats.length).toBeLessThanOrEqual(Math.floor(RULES.staleMs / RULES.heartbeatMs));
    expect(kinds(out)).not.toContain("single");
    expect(sc.isActive()).toBe(false);
  });

  it("a stale session resumes with playing_now when the page reports again", () => {
    const { sc, clock } = setup();
    const tr = track({ durationMs: 600_000 });
    sc.update("1", tr);
    run(sc, clock, 120);
    expect(kinds(sc.update("1", tr))).toEqual(["playing_now"]);
  });

  it("stops heartbeats when paused and resumes with an immediate playing_now", () => {
    const { sc, clock } = setup();
    const tr = track({ durationMs: 600_000 });
    sc.update("1", tr);
    clock.advance(10_000);
    const paused = track({ durationMs: 600_000, isPlaying: false, positionMs: 10_000 });
    sc.update("1", paused);
    expect(run(sc, clock, 120, paused)).toEqual([]);
    expect(kinds(sc.update("1", track({ durationMs: 600_000, positionMs: 10_000 })))).toEqual(["playing_now"]);
  });

  it("scrobbles once at 50% of duration with listened_at = start time", () => {
    const { sc, clock } = setup();
    const tr = track({ durationMs: 200_000 });
    sc.update("1", tr);
    expect(kinds(run(sc, clock, 95, tr))).not.toContain("single");
    const at = run(sc, clock, 5, tr);
    expect(at.find((e) => e.kind === "single")).toMatchObject({ kind: "single", listenedAt: Math.floor(T0 / 1000) });
    expect(kinds(run(sc, clock, 90, tr))).not.toContain("single");
  });

  it("scrobbles long tracks after 4 minutes", () => {
    const { sc, clock } = setup();
    const tr = track({ durationMs: 20 * 60_000 });
    sc.update("1", tr);
    expect(kinds(run(sc, clock, 235, tr))).not.toContain("single");
    expect(kinds(run(sc, clock, 5, tr))).toContain("single");
  });

  it("scrobbles unknown-duration tracks after 4 minutes", () => {
    const { sc, clock } = setup();
    const tr = track({ durationMs: undefined });
    sc.update("1", tr);
    expect(kinds(run(sc, clock, 235, tr))).not.toContain("single");
    expect(kinds(run(sc, clock, 5, tr))).toContain("single");
  });

  it("never scrobbles tracks shorter than 30 s", () => {
    const { sc, clock } = setup();
    const tr = track({ durationMs: 29_000 });
    sc.update("1", tr);
    expect(kinds(run(sc, clock, 300, tr))).not.toContain("single");
  });

  it("does not count paused time", () => {
    const { sc, clock } = setup();
    const tr = track();
    sc.update("1", tr);
    run(sc, clock, 45, tr);
    const paused = track({ isPlaying: false, positionMs: 45_000 });
    sc.update("1", paused);
    expect(kinds(run(sc, clock, 600, paused))).not.toContain("single");
  });

  it("does not count a forward seek as listening", () => {
    const { sc, clock } = setup();
    const tr = track();
    sc.update("1", tr);
    clock.advance(5000);
    expect(kinds(sc.update("1", track({ positionMs: 150_000 })))).not.toContain("single");
    expect(kinds(run(sc, clock, 90, tr))).not.toContain("single");
    expect(kinds(run(sc, clock, 10, tr))).toContain("single");
  });

  it("treats a repeat (jump back to start after a counted play) as a second scrobble", () => {
    const { sc, clock } = setup();
    const tr = track();
    sc.update("1", tr);
    const first = run(sc, clock, 195, tr);
    expect(kinds(first).filter((k) => k === "single")).toHaveLength(1);
    const restart = sc.update("1", track({ positionMs: 500 }));
    expect(kinds(restart)).toEqual(["playing_now"]);
    const singles = run(sc, clock, 105, tr).filter((e) => e.kind === "single");
    expect(singles).toHaveLength(1);
    expect(singles[0]).toMatchObject({ listenedAt: Math.floor((T0 + 195_000) / 1000) });
  });

  it("a seek back to the start before the threshold stays one play", () => {
    const { sc, clock } = setup();
    const tr = track();
    sc.update("1", tr);
    run(sc, clock, 40, tr);
    expect(sc.update("1", track({ positionMs: 0 }))).toEqual([]);
    const out = run(sc, clock, 60, tr);
    expect(out.filter((e) => e.kind === "single")).toEqual([expect.objectContaining({ listenedAt: Math.floor(T0 / 1000) })]);
  });

  it("a new track starts a new play with its own playing_now", () => {
    const { sc, clock } = setup();
    const tr = track();
    sc.update("1", tr);
    run(sc, clock, 20, tr);
    const out = sc.update("1", track({ title: "Next Song" }));
    expect(out).toEqual([expect.objectContaining({ kind: "playing_now", track: expect.objectContaining({ title: "Next Song" }) })]);
  });

  it("closing the tab ends the play without scrobbling and stops heartbeats", () => {
    const { sc, clock } = setup();
    const tr = track();
    sc.update("1", tr);
    run(sc, clock, 60, tr);
    sc.update("1", null);
    expect(run(sc, clock, 300)).toEqual([]);
  });

  it("switching a platform off ends its sessions", () => {
    const { sc, clock } = setup();
    sc.update("1", track());
    sc.endPlatform("YOUTUBE_MUSIC");
    expect(sc.isActive()).toBe(false);
    expect(run(sc, clock, 60)).toEqual([]);
  });

  it("credits no time for a long gap without page reports", () => {
    const { sc, clock } = setup();
    sc.update("1", track({ durationMs: 600_000 }));
    clock.advance(10 * 60_000);
    expect(kinds(sc.tick())).not.toContain("single");
    expect(kinds(sc.update("1", track({ durationMs: 600_000, positionMs: undefined })))).not.toContain("single");
  });

  it("survives a service-worker restart via snapshot", () => {
    const { sc, clock } = setup();
    const tr = track();
    sc.update("1", tr);
    run(sc, clock, 60, tr);
    const revived = new Scrobbler(clock.now, sc.snapshot());
    expect(kinds(run(revived, clock, 40, tr))).toContain("single");
  });
});
