import { describe, expect, it } from "vitest";
import { Scrobbler, type Emission } from "../src/background/scrobbler";
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

/** Simulate `seconds` of playback with a tick every 5 s; returns all emissions. */
function play(sc: Scrobbler, clock: { advance: (ms: number) => void }, seconds: number): Emission[] {
  const out: Emission[] = [];
  for (let s = 0; s < seconds; s += 5) {
    clock.advance(5000);
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

  it("heartbeats playing_now every 30 s while playing", () => {
    const { sc, clock } = setup();
    sc.update("1", track({ durationMs: 600_000 }));
    const out = play(sc, clock, 90);
    expect(kinds(out).filter((k) => k === "playing_now")).toHaveLength(3);
  });

  it("stops heartbeats when paused and resumes with an immediate playing_now", () => {
    const { sc, clock } = setup();
    sc.update("1", track({ durationMs: 600_000 }));
    clock.advance(10_000);
    sc.update("1", track({ durationMs: 600_000, isPlaying: false, positionMs: 10_000 }));
    expect(play(sc, clock, 120)).toEqual([]);
    expect(kinds(sc.update("1", track({ durationMs: 600_000, positionMs: 10_000 })))).toEqual(["playing_now"]);
  });

  it("scrobbles once at 50% of duration with listened_at = start time", () => {
    const { sc, clock } = setup();
    sc.update("1", track({ durationMs: 200_000 }));
    const before = play(sc, clock, 95);
    expect(kinds(before)).not.toContain("single");
    const at = play(sc, clock, 5);
    const single = at.find((e) => e.kind === "single");
    expect(single).toMatchObject({ kind: "single", listenedAt: Math.floor(T0 / 1000) });
    expect(kinds(play(sc, clock, 100))).not.toContain("single");
  });

  it("scrobbles long tracks after 4 minutes", () => {
    const { sc, clock } = setup();
    sc.update("1", track({ durationMs: 20 * 60_000 }));
    expect(kinds(play(sc, clock, 235))).not.toContain("single");
    expect(kinds(play(sc, clock, 5))).toContain("single");
  });

  it("scrobbles unknown-duration tracks after 4 minutes", () => {
    const { sc, clock } = setup();
    sc.update("1", track({ durationMs: undefined }));
    expect(kinds(play(sc, clock, 235))).not.toContain("single");
    expect(kinds(play(sc, clock, 5))).toContain("single");
  });

  it("never scrobbles tracks shorter than 30 s", () => {
    const { sc, clock } = setup();
    sc.update("1", track({ durationMs: 29_000 }));
    expect(kinds(play(sc, clock, 300))).not.toContain("single");
  });

  it("does not count paused time", () => {
    const { sc, clock } = setup();
    sc.update("1", track());
    play(sc, clock, 50);
    sc.update("1", track({ isPlaying: false, positionMs: 50_000 }));
    expect(kinds(play(sc, clock, 600))).not.toContain("single");
  });

  it("does not count a forward seek as listening", () => {
    const { sc, clock } = setup();
    sc.update("1", track());
    clock.advance(5000);
    expect(kinds(sc.update("1", track({ positionMs: 150_000 })))).not.toContain("single");
    expect(kinds(play(sc, clock, 90))).not.toContain("single");
    expect(kinds(play(sc, clock, 10))).toContain("single");
  });

  it("treats a repeat (jump back to start after a counted play) as a second scrobble", () => {
    const { sc, clock } = setup();
    sc.update("1", track());
    const first = play(sc, clock, 200);
    expect(kinds(first).filter((k) => k === "single")).toHaveLength(1);
    const restart = sc.update("1", track({ positionMs: 500 }));
    expect(kinds(restart)).toEqual(["playing_now"]);
    const second = play(sc, clock, 100);
    const singles = second.filter((e) => e.kind === "single");
    expect(singles).toHaveLength(1);
    expect(singles[0]).toMatchObject({ listenedAt: Math.floor((T0 + 200_000) / 1000) });
  });

  it("a seek back to the start before the threshold stays one play", () => {
    const { sc, clock } = setup();
    sc.update("1", track());
    play(sc, clock, 40);
    expect(sc.update("1", track({ positionMs: 0 }))).toEqual([]);
    const out = play(sc, clock, 60);
    expect(out.filter((e) => e.kind === "single")).toEqual([
      expect.objectContaining({ listenedAt: Math.floor(T0 / 1000) }),
    ]);
  });

  it("a new track starts a new play with its own playing_now", () => {
    const { sc, clock } = setup();
    sc.update("1", track());
    play(sc, clock, 20);
    const out = sc.update("1", track({ title: "Next Song" }));
    expect(out).toEqual([expect.objectContaining({ kind: "playing_now", track: expect.objectContaining({ title: "Next Song" }) })]);
  });

  it("closing the tab ends the play without scrobbling and stops heartbeats", () => {
    const { sc, clock } = setup();
    sc.update("1", track());
    play(sc, clock, 60);
    sc.update("1", null);
    expect(play(sc, clock, 300)).toEqual([]);
  });

  it("caps credit for long gaps between updates", () => {
    const { sc, clock } = setup();
    sc.update("1", track({ durationMs: 600_000 }));
    clock.advance(10 * 60_000);
    expect(kinds(sc.tick())).not.toContain("single");
  });

  it("survives a service-worker restart via snapshot", () => {
    const { sc, clock } = setup();
    sc.update("1", track());
    play(sc, clock, 60);
    const revived = new Scrobbler(clock.now, sc.snapshot());
    expect(kinds(play(revived, clock, 40))).toContain("single");
  });
});
