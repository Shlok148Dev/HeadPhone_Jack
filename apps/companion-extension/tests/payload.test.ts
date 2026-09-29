import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { buildSubmission } from "../src/background/payload";
import { VERSION } from "../src/shared/version";
import type { TrackState } from "../src/shared/types";

const t: TrackState = {
  platform: "YOUTUBE_MUSIC",
  artist: "Artist",
  title: "Song",
  album: "Album",
  durationMs: 213000,
  positionMs: 1000,
  isPlaying: true,
  originUrl: "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
  artworkUrl: "https://lh3.example/a",
};

describe("ListenBrainz payload", () => {
  it("single matches the LB submit-listens format", () => {
    expect(buildSubmission("single", t, 1790000000)).toMatchInlineSnapshot(`
      {
        "listen_type": "single",
        "payload": [
          {
            "listened_at": 1790000000,
            "track_metadata": {
              "additional_info": {
                "duration_ms": 213000,
                "music_service": "music.youtube.com",
                "origin_url": "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
                "submission_client": "Jingle Companion",
                "submission_client_version": "0.1.0",
              },
              "artist_name": "Artist",
              "release_name": "Album",
              "track_name": "Song",
            },
          },
        ],
      }
    `);
  });

  it("playing_now has no listened_at and omits missing optionals", () => {
    const body = buildSubmission("playing_now", { platform: "AMAZON_MUSIC", artist: "A", title: "T", isPlaying: true });
    expect(body).toEqual({
      listen_type: "playing_now",
      payload: [
        {
          track_metadata: {
            artist_name: "A",
            track_name: "T",
            additional_info: { music_service: "music.amazon.com", submission_client: "Jingle Companion", submission_client_version: VERSION },
          },
        },
      ],
    });
  });

  it("maps every platform to its web-player host", () => {
    const svc = (p: TrackState["platform"]) =>
      buildSubmission("playing_now", { platform: p, artist: "a", title: "t", isPlaying: true }).payload[0].track_metadata.additional_info.music_service;
    expect([svc("YOUTUBE_MUSIC"), svc("SPOTIFY"), svc("APPLE_MUSIC"), svc("AMAZON_MUSIC")]).toEqual([
      "music.youtube.com",
      "open.spotify.com",
      "music.apple.com",
      "music.amazon.com",
    ]);
  });

  it("version is consistent across code, package.json and manifest", () => {
    const pkg = JSON.parse(readFileSync(resolve(__dirname, "../package.json"), "utf8")) as { version: string };
    const manifest = JSON.parse(readFileSync(resolve(__dirname, "../public/manifest.json"), "utf8")) as { version: string };
    expect(pkg.version).toBe(VERSION);
    expect(manifest.version).toBe(VERSION);
  });
});
