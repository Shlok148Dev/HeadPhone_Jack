import { beforeEach, describe, expect, it } from "vitest";
import { amazonMusic, appleMusic, connectorForHost, spotify, youtubeMusic } from "../src/connectors";
import { parseClock, pickArtwork } from "../src/connectors/common";
import { env, loadFixture, mediaSession, setMedia } from "./helpers";

beforeEach(() => {
  document.body.innerHTML = "";
});

describe("youtube-music connector", () => {
  const url = "https://music.youtube.com/watch?v=dQw4w9WgXcQ&list=RDAMVM";

  it("reads MediaSession + the page <video>", () => {
    loadFixture("youtube-music.html");
    setMedia("video", { currentTime: 42.5, duration: 213, paused: false });
    const ms = mediaSession({
      title: "Session Song",
      artist: "Session Artist",
      album: "Session Album",
      artwork: [
        { src: "https://lh3.example/a=w60", sizes: "60x60" },
        { src: "https://lh3.example/a=w544", sizes: "544x544" },
      ],
    });
    expect(youtubeMusic.read(env(ms, url))).toEqual({
      platform: "YOUTUBE_MUSIC",
      artist: "Session Artist",
      title: "Session Song",
      album: "Session Album",
      durationMs: 213000,
      positionMs: 42500,
      isPlaying: true,
      originUrl: "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
      artworkUrl: "https://lh3.example/a=w544",
    });
  });

  it("falls back to the player bar when MediaSession has no metadata", () => {
    loadFixture("youtube-music.html");
    setMedia("video", { currentTime: 1, duration: 200, paused: true });
    const s = youtubeMusic.read(env(mediaSession(null, "none"), url));
    expect(s).toMatchObject({ title: "Fixture Song", artist: "Fixture Artist", isPlaying: false, durationMs: 200000 });
  });

  it("skips ads", () => {
    loadFixture("youtube-music.html");
    document.getElementById("movie_player")!.classList.add("ad-showing");
    expect(youtubeMusic.read(env(mediaSession({ title: "Ad", artist: "Brand" }), url))).toBeNull();
  });

  it("ignores a malformed video id", () => {
    loadFixture("youtube-music.html");
    const s = youtubeMusic.read(env(mediaSession({ title: "T", artist: "A" }), "https://music.youtube.com/watch?v=<script>"));
    expect(s?.originUrl).toBeUndefined();
  });
});

describe("spotify connector", () => {
  it("reads MediaSession and falls back to the player-bar clock (no media element)", () => {
    loadFixture("spotify.html");
    const s = spotify.read(env(mediaSession({ title: "Session Song", artist: "Session Artist", album: "LP" }, "playing"), "https://open.spotify.com/"));
    expect(s).toEqual({
      platform: "SPOTIFY",
      artist: "Session Artist",
      title: "Session Song",
      album: "LP",
      durationMs: 210000,
      positionMs: 65000,
      isPlaying: true,
      originUrl: "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
    });
  });

  it("handles the 'remaining time' duration label and paused state", () => {
    loadFixture("spotify.html");
    document.querySelector('[data-testid="playback-duration"]')!.textContent = "-2:25";
    const s = spotify.read(env(mediaSession({ title: "S", artist: "A" }, "paused"), "https://open.spotify.com/"));
    expect(s).toMatchObject({ durationMs: 210000, positionMs: 65000, isPlaying: false });
  });

  it("returns null without MediaSession metadata (no DOM guessing of identity)", () => {
    loadFixture("spotify.html");
    expect(spotify.read(env(mediaSession(null, "none"), "https://open.spotify.com/"))).toBeNull();
  });
});

describe("apple-music connector", () => {
  it("reads MediaSession + <audio>", () => {
    loadFixture("apple-music.html");
    setMedia("audio", { currentTime: 10, duration: 180.4, paused: false });
    const url = "https://music.apple.com/in/song/fixture-song/1234567890";
    expect(appleMusic.read(env(mediaSession({ title: "Song", artist: "Artist", album: "Album" }), url))).toEqual({
      platform: "APPLE_MUSIC",
      artist: "Artist",
      title: "Song",
      album: "Album",
      durationMs: 180400,
      positionMs: 10000,
      isPlaying: true,
      originUrl: url,
    });
  });

  it("media element pause wins over MediaSession playbackState", () => {
    loadFixture("apple-music.html");
    setMedia("audio", { currentTime: 10, duration: 180, paused: true });
    const s = appleMusic.read(env(mediaSession({ title: "Song", artist: "Artist" }, "playing"), "https://music.apple.com/in/browse"));
    expect(s).toMatchObject({ isPlaying: false });
    expect(s?.originUrl).toBeUndefined();
  });
});

describe("amazon-music connector", () => {
  it("reads MediaSession + <audio>", () => {
    loadFixture("amazon-music.html");
    setMedia("audio", { currentTime: 30, duration: 240, paused: false });
    expect(amazonMusic.read(env(mediaSession({ title: "Song", artist: "Artist" }), "https://music.amazon.in/my/library"))).toEqual({
      platform: "AMAZON_MUSIC",
      artist: "Artist",
      title: "Song",
      durationMs: 240000,
      positionMs: 30000,
      isPlaying: true,
    });
  });

  it("requires an artist", () => {
    loadFixture("amazon-music.html");
    expect(amazonMusic.read(env(mediaSession({ title: "Song", artist: "  " }), "https://music.amazon.com/"))).toBeNull();
  });
});

describe("connector helpers", () => {
  it("maps hosts, including Amazon regional hosts", () => {
    expect(connectorForHost("music.youtube.com")?.platform).toBe("YOUTUBE_MUSIC");
    expect(connectorForHost("music.amazon.co.uk")?.platform).toBe("AMAZON_MUSIC");
    expect(connectorForHost("www.youtube.com")).toBeUndefined();
  });

  it("parses clocks", () => {
    expect(parseClock("3:05")).toBe(185000);
    expect(parseClock("1:02:03")).toBe(3723000);
    expect(parseClock("-0:42")).toBe(-42000);
    expect(parseClock("live")).toBeUndefined();
  });

  it("ignores non-https artwork", () => {
    expect(pickArtwork([{ src: "data:image/png;base64,xx", sizes: "999x999" }])).toBeUndefined();
  });
});
