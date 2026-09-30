import { describe, expect, it } from "vitest";
import { openTarget, type Song } from "./sends";

const song = (links: Song["links"]): Song => ({
  recording_id: "r1",
  title: "Blue",
  artist: "Yung Kai",
  links,
  search_links: { APPLE_MUSIC: "https://music.apple.com/search?term=Blue", SPOTIFY: "https://open.spotify.com/search/Blue" },
});

describe("openTarget (JNG-06-03 Gherkin, client half)", () => {
  it("deep-links to the Apple Music version for an Apple Music friend", () => {
    const t = openTarget(song({ SPOTIFY: "https://open.spotify.com/track/x", APPLE_MUSIC: "https://music.apple.com/in/song/1" }), "APPLE_MUSIC");
    expect(t).toEqual({ url: "https://music.apple.com/in/song/1", label: "Open in Apple Music", notFound: null });
  });

  it('says "Not found on Apple Music" and offers a search when there is no match', () => {
    const t = openTarget(song({ SPOTIFY: "https://open.spotify.com/track/x", APPLE_MUSIC: null }), "APPLE_MUSIC");
    expect(t).toEqual({ url: "https://music.apple.com/search?term=Blue", label: "Search in Apple Music", notFound: "Not found on Apple Music" });
  });

  it("falls back to any verified link when I have no platform", () => {
    expect(openTarget(song({ SPOTIFY: "https://open.spotify.com/track/x" }), undefined)?.label).toBe("Open in Spotify");
    expect(openTarget(song({}), "UNKNOWN")).toBeNull();
  });
});
