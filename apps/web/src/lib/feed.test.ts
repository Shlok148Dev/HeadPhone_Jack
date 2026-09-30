import { describe, expect, it } from "vitest";
import type { FeedCardData } from "@/components/ds";
import { isFreshLive, sortFeed } from "./feed";

const card = (name: string, state: FeedCardData["state"], observed?: string): FeedCardData => ({
  friend: { id: name, username: name, display_name: name, avatar_url: null },
  state,
  platform: "SPOTIFY",
  recording: null,
  observed_at: observed ?? null,
  freshness_label: "",
  degraded: false,
  attribution: null,
});

describe("feed ordering and the client-side Live guard", () => {
  it("orders Live, newest Recent, Top, Hidden (BR-02)", () => {
    const out = sortFeed([
      card("h", "HIDDEN"),
      card("t", "TOP"),
      card("old", "RECENT", "2026-09-30T10:00:00Z"),
      card("new", "RECENT", "2026-09-30T11:00:00Z"),
      card("live", "LIVE", "2026-09-30T11:59:00Z"),
    ]);
    expect(out.map((c) => c.friend.id)).toEqual(["live", "new", "old", "t", "h"]);
  });

  it("stops treating a card as Live 90 s after its signal (BR-01)", () => {
    const now = Date.parse("2026-09-30T12:00:00Z");
    expect(isFreshLive(card("a", "LIVE", "2026-09-30T11:58:31Z"), now)).toBe(true);
    expect(isFreshLive(card("a", "LIVE", "2026-09-30T11:58:30Z"), now)).toBe(false);
    expect(isFreshLive(card("a", "RECENT", "2026-09-30T11:59:59Z"), now)).toBe(false);
  });
});
