import { describe, expect, it } from "vitest";
import { applyDelta, type SessionState } from "./live";

const base: SessionState = {
  id: "s",
  title: "Room",
  host: { id: "h", username: "h", display_name: "H" },
  ended: false,
  now_playing: null,
  queue: [
    { id: "a", recording_id: null, title: "A", artist: "X", added_by: null, score: 0 },
    { id: "b", recording_id: null, title: "B", artist: "X", added_by: null, score: 0 },
  ],
  participants: [],
  version: 5,
  my_votes: { a: 1, gone: -1 },
  joined: true,
  now_playing_links: null,
};

describe("applyDelta (JNG-07-07/09)", () => {
  it("applies newer versions and keeps my votes for entries still queued", () => {
    const queue = [{ ...base.queue[1]!, score: 2 }, base.queue[0]!];
    const next = applyDelta(base, 6, { ...base, queue });
    expect(next?.version).toBe(6);
    expect(next?.queue.map((e) => e.id)).toEqual(["b", "a"]);
    expect(next?.my_votes).toEqual({ a: 1 });
  });

  it("ignores stale or repeated versions", () => {
    expect(applyDelta(base, 5, { ...base, queue: [] })).toBe(base);
    expect(applyDelta(base, 3, { ...base, queue: [] })).toBe(base);
  });

  it("asks for a REST refetch when it has no state or the song changed (fresh links)", () => {
    expect(applyDelta(undefined, 9, base)).toBeNull();
    expect(applyDelta(base, 7, { ...base, now_playing: base.queue[0]! })).toBeNull();
  });
});
